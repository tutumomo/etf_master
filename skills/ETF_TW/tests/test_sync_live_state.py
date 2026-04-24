from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_live_state.py")
spec = importlib.util.spec_from_file_location("sync_live_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_live_positions_payload_marks_source_live_broker():
    positions = [
        type("Pos", (), {"symbol": "0050", "quantity": 1000, "average_price": 180.0, "current_price": 182.0, "market_value": 182000.0, "unrealized_pnl": 2000.0})()
    ]
    payload = module.build_live_positions_payload(positions, "2026-03-30T18:00:00")
    assert payload["source"] == "live_broker"
    assert payload["positions"][0]["symbol"] == "0050"


def test_build_live_account_snapshot_marks_source_live_broker():
    balance = type("Bal", (), {"cash_available": 30000.0, "market_value": 182000.0, "total_value": 212000.0})()
    payload = module.build_live_account_snapshot(balance, position_count=1, updated_at="2026-03-30T18:00:00")
    assert payload["source"] == "live_broker"
    assert payload["position_count"] == 1
    assert payload["settlement_safe_cash"] == 30000.0


def test_build_live_account_snapshot_calculates_settlement_safe_cash_from_t1_t2_only():
    balance = type("Bal", (), {"cash_available": 59235.0, "market_value": 0.0, "total_value": 59235.0})()
    settlements = [
        {"date": "2026-04-24", "T": 0, "amount": -39317.0},
        {"date": "2026-04-27", "T": 1, "amount": -30330.0},
        {"date": "2026-04-28", "T": 2, "amount": -9173.0},
    ]
    payload = module.build_live_account_snapshot(
        balance,
        position_count=7,
        updated_at="2026-04-24T21:57:30",
        settlements=settlements,
    )
    assert payload["future_settlement_net_t1_t2"] == -39503.0
    assert payload["settlement_safe_cash"] == 19732.0
    assert payload["settlement_safe_cash_floor"] == 19732.0


def test_build_live_account_snapshot_keeps_negative_safe_cash_but_floors_display_value():
    balance = type("Bal", (), {"cash_available": 10000.0, "market_value": 0.0, "total_value": 10000.0})()
    payload = module.build_live_account_snapshot(
        balance,
        position_count=0,
        updated_at="2026-04-24T21:57:30",
        settlements=[{"date": "2026-04-27", "T": 1, "amount": -30330.0}],
    )
    assert payload["settlement_safe_cash"] == -20330.0
    assert payload["settlement_safe_cash_floor"] == 0


def test_should_sync_live_state_only_for_live_ready_mode():
    assert module.should_sync_live_state({"effective_mode": "live-ready"}) is True
    assert module.should_sync_live_state({"effective_mode": "paper"}) is False


def test_build_live_positions_payload_keeps_share_quantity():
    positions = [
        type("Pos", (), {"symbol": "0050", "quantity": 203, "average_price": 74.65, "current_price": 73.9, "market_value": 14991.7, "unrealized_pnl": -187.0})()
    ]
    payload = module.build_live_positions_payload(positions, "2026-03-30T19:00:00")
    assert payload["positions"][0]["quantity"] == 203
