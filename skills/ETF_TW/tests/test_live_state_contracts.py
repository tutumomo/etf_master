from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

LIVE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_live_state.py")
live_spec = importlib.util.spec_from_file_location("sync_live_state", LIVE_MODULE_PATH)
sync_live_state = importlib.util.module_from_spec(live_spec)
live_spec.loader.exec_module(sync_live_state)

SNAPSHOT_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_portfolio_snapshot.py")
snapshot_spec = importlib.util.spec_from_file_location("sync_portfolio_snapshot", SNAPSHOT_MODULE_PATH)
sync_portfolio_snapshot = importlib.util.module_from_spec(snapshot_spec)
snapshot_spec.loader.exec_module(sync_portfolio_snapshot)


def test_live_positions_payload_marks_every_row_live_broker():
    positions = [
        type("Pos", (), {
            "symbol": "0050",
            "quantity": 253,
            "average_price": 74.54,
            "current_price": 73.95,
            "market_value": 18709.35,
            "unrealized_pnl": -193.0,
        })(),
        type("Pos", (), {
            "symbol": "00878",
            "quantity": 100,
            "average_price": 22.42,
            "current_price": 22.03,
            "market_value": 2203.0,
            "unrealized_pnl": -44.0,
        })(),
    ]
    payload = sync_live_state.build_live_positions_payload(positions, "2026-04-02T20:00:00")
    assert payload["source"] == "live_broker"
    assert all(row["source"] == "live_broker" for row in payload["positions"])
    assert payload["positions"][0]["quantity"] == 253


def test_live_snapshot_uses_positions_and_cash_to_build_total_equity():
    account_snapshot = {
        "cash": 12605.0,
        "source": "live_broker",
    }
    positions_snapshot = {
        "positions": [
            {
                "symbol": "0050",
                "quantity": 253,
                "average_price": 74.54,
                "current_price": 73.95,
                "market_value": 18709.35,
                "unrealized_pnl": -193.0,
            },
            {
                "symbol": "00878",
                "quantity": 100,
                "average_price": 22.42,
                "current_price": 22.03,
                "market_value": 2203.0,
                "unrealized_pnl": -44.0,
            },
        ]
    }
    payload = sync_portfolio_snapshot.build_snapshot_from_live_state_payloads(account_snapshot, positions_snapshot, "2026-04-02T20:00:00")
    assert payload["source"] == "live_broker"
    assert payload["cash"] == 12605.0
    assert payload["market_value"] == 20912.35
    assert payload["total_equity"] == 33517.35
    assert len(payload["holdings"]) == 2
