from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

BASE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/adapters/base.py")
base_spec = importlib.util.spec_from_file_location("adapter_base", BASE_MODULE_PATH)
adapter_base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(adapter_base)

LIVE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_live_state.py")
live_spec = importlib.util.spec_from_file_location("sync_live_state", LIVE_MODULE_PATH)
sync_live_state = importlib.util.module_from_spec(live_spec)
live_spec.loader.exec_module(sync_live_state)

VALID_STATUSES = {"pending", "submitted", "filled", "cancelled", "rejected"}


def test_base_order_status_default_is_valid():
    order = adapter_base.Order(symbol="0050", action="buy", quantity=100)
    assert order.status in VALID_STATUSES


def test_order_status_contract_set_is_explicit():
    assert VALID_STATUSES == {"pending", "submitted", "filled", "cancelled", "rejected"}


def test_live_positions_payload_does_not_embed_order_status_noise():
    positions = [
        type("Pos", (), {
            "symbol": "0050",
            "quantity": 100,
            "average_price": 74.0,
            "current_price": 75.0,
            "market_value": 7500.0,
            "unrealized_pnl": 100.0,
        })()
    ]
    payload = sync_live_state.build_live_positions_payload(positions, "2026-04-02T21:00:00")
    row = payload["positions"][0]
    assert "status" not in row
    assert row["source"] == "live_broker"


def test_orders_open_contract_example_uses_submitted_style_state_only():
    payload = {
        "orders": [
            {
                "order_id": "43e14cbd",
                "seqno": "368326",
                "ordno": "Y0E6D",
                "symbol": "00922",
                "action": "buy",
                "quantity": 50,
                "price": 27.45,
                "mode": "live",
                "status": "submitted",
                "source": "live_broker",
            }
        ],
        "source": "live_broker",
    }
    assert payload["orders"][0]["status"] in VALID_STATUSES
    assert payload["orders"][0]["status"] == "submitted"
