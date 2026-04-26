import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.auto_trade import ack_handler, pending_queue
from scripts.auto_trade.vwap_calculator import TW_TZ


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
            "effective_mode": "live-ready",
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
        return SimpleNamespace(returncode=0, stdout="VERIFIED broker_order_id=ABC123", stderr="")

    monkeypatch.setattr(ack_handler.subprocess, "run", fake_run)

    output, ok = ack_handler._invoke_complete_trade(signal, state_dir=tmp_path)

    assert ok is True
    assert "broker_order_id=ABC123" in output
    cmd = captured["cmd"]
    assert cmd[1].endswith("scripts/complete_trade.py")
    assert cmd[2:5] == ["0050", "buy", "100"]
    assert "--price" in cmd and cmd[cmd.index("--price") + 1] == "50.0"
    assert "--mode" in cmd and cmd[cmd.index("--mode") + 1] == "live"
    assert "--broker" in cmd and cmd[cmd.index("--broker") + 1] == "sinopac"
    assert "--account" in cmd and cmd[cmd.index("--account") + 1] == "sinopac_01"
    assert "--decision-id" in cmd and cmd[cmd.index("--decision-id") + 1] == "sig-123"
