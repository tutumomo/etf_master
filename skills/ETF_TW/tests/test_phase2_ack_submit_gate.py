import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.auto_trade import ack_handler, pending_queue
from scripts.auto_trade.vwap_calculator import TW_TZ
from scripts.auto_trade.initial_dca import load_dca_state


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _enqueue_signal(state_dir: Path) -> dict:
    return pending_queue.enqueue(
        queue_path=state_dir / "pending_auto_orders.json",
        history_path=state_dir / "auto_trade_history.jsonl",
        side="buy",
        symbol="0050",
        quantity=100,
        price=50.0,
        order_type="limit",
        lot_type="odd",
        trigger_source="test",
        trigger_reason="unit test",
        now=datetime.now(tz=TW_TZ),
    )


def test_phase2_ack_blocks_outside_trading_hours_before_subprocess(tmp_path, monkeypatch):
    signal = _enqueue_signal(tmp_path)
    _write_json(tmp_path / "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_json(tmp_path / "positions.json", {"positions": []})

    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("complete_trade.py must not run outside trading hours")

    monkeypatch.setattr(ack_handler.subprocess, "run", fake_run)
    monkeypatch.setattr(
        ack_handler.pre_flight,
        "get_trading_hours_info",
        lambda: {"is_trading_hours": False, "current_time": "2026-04-26T10:00:00+08:00"},
    )

    result = ack_handler.ack_signal(signal["id"], state_dir=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "gate_blocked"
    assert result["reason"] == "outside_trading_hours"
    assert called is False


def test_phase2_ack_blocks_when_settlement_safe_cash_is_zero(tmp_path, monkeypatch):
    signal = _enqueue_signal(tmp_path)
    _write_json(tmp_path / "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 0})
    _write_json(tmp_path / "positions.json", {"positions": []})
    _write_json(tmp_path / "safety_redlines.json", {
        "max_buy_amount_pct": 0.5,
        "max_buy_amount_twd": 500000,
        "max_buy_shares": 1000,
    })

    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("complete_trade.py must not run with zero settlement-safe cash")

    monkeypatch.setattr(ack_handler.subprocess, "run", fake_run)
    monkeypatch.setattr(
        ack_handler.pre_flight,
        "get_trading_hours_info",
        lambda: {"is_trading_hours": True, "current_time": "2026-04-26T10:00:00+08:00"},
    )

    result = ack_handler.ack_signal(signal["id"], state_dir=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "gate_blocked"
    assert result["reason"] == "exceeds_sizing_limit"
    assert result["gate_details"]["sizing_base"] == "settlement_safe_cash"
    assert called is False


def test_phase2_complete_trade_command_matches_dashboard_submit_shape(tmp_path, monkeypatch):
    _write_json(
        tmp_path / "trading_mode.json",
        {
            "effective_mode": "paper",
            "default_broker": "sinopac",
            "default_account": "sinopac_01",
        },
    )
    signal = {
        "id": "sig-123",
        "symbol": "0050",
        "side": "buy",
        "quantity": 100,
        "price": 50.0,
    }
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="驗證結果：VERIFIED\nbroker_order_id=ABC123", stderr="")

    monkeypatch.setattr(ack_handler.subprocess, "run", fake_run)

    output, ok = ack_handler._invoke_complete_trade(signal, state_dir=tmp_path)

    assert ok is True
    assert "broker_order_id=ABC123" in output
    cmd = captured["cmd"]
    assert cmd[1].endswith("scripts/complete_trade.py")
    assert cmd[2:5] == ["0050", "buy", "100"]
    assert "--price" in cmd and cmd[cmd.index("--price") + 1] == "50.0"
    assert "--mode" in cmd and cmd[cmd.index("--mode") + 1] == "paper"
    assert "--broker" in cmd and cmd[cmd.index("--broker") + 1] == "sinopac"
    assert "--account" in cmd and cmd[cmd.index("--account") + 1] == "sinopac_01"
    assert "--decision-id" in cmd and cmd[cmd.index("--decision-id") + 1] == "sig-123"


def test_phase2_live_ack_does_not_treat_unverified_as_success():
    assert ack_handler._complete_trade_output_verified("驗證結果：UNVERIFIED") is False
    assert ack_handler._complete_trade_output_verified("驗證結果：VERIFIED") is True


def test_phase2_live_ack_uses_live_submit_sop(tmp_path, monkeypatch):
    _write_json(
        tmp_path / "trading_mode.json",
        {
            "effective_mode": "live-ready",
            "default_broker": "sinopac",
            "default_account": "sinopac_01",
        },
    )
    signal = {
        "id": "sig-live-123",
        "symbol": "0050",
        "side": "buy",
        "quantity": 100,
        "price": 50.0,
        "order_type": "limit",
        "lot_type": "odd",
    }
    captured = {}

    async def fake_submit_live_order(order, state_dir):
        captured["order"] = order
        captured["state_dir"] = state_dir
        return {
            "success": True,
            "verified": True,
            "ghost": False,
            "broker_order_id": "ORD-LIVE",
            "order_id": order["order_id"],
        }

    monkeypatch.setattr("scripts.live_submit_sop.submit_live_order", fake_submit_live_order)
    monkeypatch.setattr(
        ack_handler.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live ack must not call complete_trade.py")),
    )

    output, ok = ack_handler._invoke_complete_trade(signal, state_dir=tmp_path)

    assert ok is True
    assert "ORD-LIVE" in output
    assert captured["order"]["order_id"] == "sig-live-123"
    assert captured["order"]["account_id"] == "sinopac_01"
    assert captured["order"]["broker_id"] == "sinopac"


def test_phase2_ack_records_initial_dca_after_execution(tmp_path, monkeypatch):
    _write_json(tmp_path / "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_json(tmp_path / "positions.json", {"positions": []})
    _write_json(tmp_path / "safety_redlines.json", {
        "max_buy_amount_pct": 0.5,
        "max_buy_amount_twd": 500000,
        "max_buy_shares": 1000,
    })
    _write_json(tmp_path / "initial_dca_state.json", {
        "enabled": True,
        "total_target_twd": 10000,
        "target_days": 10,
        "started_on": "2026-04-29",
        "days_done": 0,
        "twd_spent": 0,
        "completed": False,
        "last_buy_date": None,
        "symbol_priority": ["0050"],
        "next_symbol_idx": 0,
    })
    signal = pending_queue.enqueue(
        queue_path=tmp_path / "pending_auto_orders.json",
        history_path=tmp_path / "auto_trade_history.jsonl",
        side="buy",
        symbol="0050",
        quantity=20,
        price=50.0,
        order_type="limit",
        lot_type="odd",
        trigger_source="initial_dca",
        trigger_reason="initial DCA",
        trigger_payload={
            "initial_dca": True,
            "amount_twd": 1000,
            "next_symbol_idx": 0,
        },
        now=datetime(2026, 4, 29, 9, 30, tzinfo=TW_TZ),
    )
    monkeypatch.setattr(
        ack_handler.pre_flight,
        "get_trading_hours_info",
        lambda: {"is_trading_hours": True, "current_time": "2026-04-29T10:00:00+08:00"},
    )
    monkeypatch.setattr(ack_handler, "_now", lambda: datetime(2026, 4, 29, 9, 40, tzinfo=TW_TZ))

    result = ack_handler.ack_signal(signal["id"], state_dir=tmp_path, skip_complete_trade=True)

    assert result["ok"] is True
    assert result["status"] == "executed"
    dca_state = load_dca_state(tmp_path)
    assert dca_state["days_done"] == 1
    assert dca_state["twd_spent"] == 1000
    assert dca_state["last_buy_date"] == "2026-04-29"
