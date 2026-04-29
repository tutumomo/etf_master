import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fastapi.testclient import TestClient

from dashboard import app as dashboard_app
from dashboard.app import app, build_trade_preview_id, submit_stdout_verified


client = TestClient(app)
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "dashboard" / "templates" / "overview.html"


def _payload(**overrides):
    payload = {
        "symbol": "0050",
        "side": "buy",
        "quantity": 100,
        "price": 50.0,
        "preview_id": build_trade_preview_id("0050", "buy", 100, 50.0),
        "confirmation": "CONFIRM 0050 buy 100",
    }
    payload.update(overrides)
    return payload


def test_trade_preview_returns_submit_confirmation_contract():
    resp = client.post(
        "/api/trade/preview",
        json={"symbol": "0050", "side": "buy", "quantity": 100, "price": 50.0},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["preview_id"] == build_trade_preview_id("0050", "buy", 100, 50.0)
    assert body["confirmation_required"] == "CONFIRM 0050 buy 100"


def test_submit_stdout_verified_does_not_match_unverified_substring():
    assert submit_stdout_verified("6. 最終狀態：SUBMITTED\n   驗證結果：UNVERIFIED") is False
    assert submit_stdout_verified("6. 最終狀態：SUBMITTED\n   驗證結果：VERIFIED") is True


def test_trade_submit_button_preserves_ticket_clean_id():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "onclick=\"executeTrade('${symbol}', '${cleanId}')\"" in text
    assert "async function executeTrade(symbol, cleanIdOverride)" in text
    assert "const cleanId = cleanIdOverride || symbol.replace('.', '');" in text
    assert "Preview Only" not in text


def test_trade_submit_rejects_wrong_confirmation_before_execution(monkeypatch):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(dashboard_app.subprocess, "run", fake_run)
    resp = client.post("/api/trade/submit", json=_payload(confirmation="wrong"))

    assert resp.status_code == 400
    assert "確認文字不符" in resp.json()["detail"]
    assert called is False


def test_trade_submit_rejects_preview_id_mismatch_before_execution(monkeypatch):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(dashboard_app.subprocess, "run", fake_run)
    resp = client.post("/api/trade/submit", json=_payload(preview_id="stale-preview"))

    assert resp.status_code == 400
    assert "preview_id 不符" in resp.json()["detail"]
    assert called is False


def test_trade_submit_blocks_outside_trading_hours_before_execution(monkeypatch):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(dashboard_app.subprocess, "run", fake_run)
    monkeypatch.setattr(
        dashboard_app.pre_flight,
        "get_trading_hours_info",
        lambda: {"is_trading_hours": False, "current_time": "2026-04-26T10:00:00+08:00"},
    )

    resp = client.post("/api/trade/submit", json=_payload())

    assert resp.status_code == 403
    assert "outside_trading_hours" in resp.json()["detail"]
    assert called is False


def test_live_trade_submit_uses_live_submit_sop_and_rejects_ghost(monkeypatch):
    monkeypatch.setattr(
        dashboard_app,
        "build_overview_model",
        lambda: {
            "account": {"cash": 100000, "settlement_safe_cash": 100000, "total_equity": 200000},
            "positions": {"positions": []},
            "trading_mode": {
                "effective_mode": "live-ready",
                "default_broker": "sinopac",
                "default_account": "sinopac_01",
            },
        },
    )
    monkeypatch.setattr(
        dashboard_app.pre_flight,
        "check_order",
        lambda order, ctx: {"passed": True, "reason": "passed", "details": {}},
    )
    monkeypatch.setattr(
        dashboard_app,
        "safe_load_json",
        lambda path, default=None: {"enabled": True} if str(path).endswith("live_mode.json") else (default or {}),
    )
    monkeypatch.setattr(
        dashboard_app.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live submit must not call complete_trade.py")),
    )

    async def fake_submit_live_order(order, state_dir):
        return {
            "success": False,
            "verified": False,
            "ghost": True,
            "reason": "verify_order_landed: ordno not found after 3 polls",
            "order_id": order["order_id"],
        }

    monkeypatch.setattr("scripts.live_submit_sop.submit_live_order", fake_submit_live_order)

    resp = client.post("/api/trade/submit", json=_payload())

    assert resp.status_code == 502
    assert "ordno not found" in resp.json()["detail"]


def test_live_trade_submit_returns_verified_sop_result(monkeypatch):
    monkeypatch.setattr(
        dashboard_app,
        "build_overview_model",
        lambda: {
            "account": {"cash": 100000, "settlement_safe_cash": 100000, "total_equity": 200000},
            "positions": {"positions": []},
            "trading_mode": {
                "effective_mode": "live-ready",
                "default_broker": "sinopac",
                "default_account": "sinopac_01",
            },
        },
    )
    monkeypatch.setattr(
        dashboard_app.pre_flight,
        "check_order",
        lambda order, ctx: {"passed": True, "reason": "passed", "details": {}},
    )
    monkeypatch.setattr(
        dashboard_app,
        "safe_load_json",
        lambda path, default=None: {"enabled": True} if str(path).endswith("live_mode.json") else (default or {}),
    )
    captured = {}

    async def fake_submit_live_order(order, state_dir):
        captured["order"] = order
        return {
            "success": True,
            "verified": True,
            "ghost": False,
            "broker_order_id": "ORD-DASH",
            "order_id": order["order_id"],
        }

    monkeypatch.setattr("scripts.live_submit_sop.submit_live_order", fake_submit_live_order)

    resp = client.post("/api/trade/submit", json=_payload())

    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["broker_order_id"] == "ORD-DASH"
    assert captured["order"]["order_id"] == _payload()["preview_id"]


def test_auto_trade_live_submit_uses_live_submit_sop(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_app, "STATE", tmp_path)
    (tmp_path / "auto_preview_candidate.json").write_text(
        """{
          "symbol": "0050",
          "not_submitted": true,
          "generated_at": "2026-04-29T09:00:00+08:00"
        }""",
        encoding="utf-8",
    )
    (tmp_path / "auto_trade_config.json").write_text('{"live_submit_allowed": true}', encoding="utf-8")
    (tmp_path / "auto_trade_state.json").write_text('{"live_submit_allowed": true}', encoding="utf-8")
    (tmp_path / "trading_mode.json").write_text(
        '{"default_broker": "sinopac", "default_account": "sinopac_01"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dashboard_app.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live submit must not call complete_trade.py")),
    )
    captured = {}

    async def fake_submit_live_order(order, state_dir):
        captured["order"] = order
        captured["state_dir"] = state_dir
        return {
            "success": True,
            "verified": True,
            "ghost": False,
            "broker_order_id": "ORD-AUTO",
            "order_id": order["order_id"],
        }

    monkeypatch.setattr("scripts.live_submit_sop.submit_live_order", fake_submit_live_order)

    resp = client.post(
        "/api/auto-trade/submit",
        json={
            "symbol": "0050",
            "action": "buy",
            "quantity": 100,
            "price": 50.0,
            "mode": "live",
            "confirmation": "CONFIRM 0050 buy 100",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["verified"] is True
    assert body["broker_order_id"] == "ORD-AUTO"
    assert captured["order"]["account_id"] == "sinopac_01"
    assert captured["order"]["broker_id"] == "sinopac"
