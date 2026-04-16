from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_event_bridge.py")
spec = importlib.util.spec_from_file_location("order_event_bridge", MODULE_PATH)
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)


def test_partial_fill_event_row_contains_minimum_fill_facts():
    row = bridge_module.event_payload_to_order_row("status_update", {
        "order_id": "pf-001",
        "symbol": "00922",
        "action": "buy",
        "status": "partial_filled",
        "filled_quantity": 300,
        "remaining_quantity": 700,
        "price": 27.45,
    })
    assert row["status"] == "partial_filled"
    assert row["filled_quantity"] == 300
    assert row["remaining_quantity"] == 700
    assert row["source_type"] == "broker_callback"
    assert "observed_at" in row
