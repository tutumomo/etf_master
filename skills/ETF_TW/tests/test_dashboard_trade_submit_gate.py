import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fastapi.testclient import TestClient

from dashboard import app as dashboard_app
from dashboard.app import app, build_trade_preview_id


client = TestClient(app)


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
