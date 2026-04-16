from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_event_bridge.py")
spec = importlib.util.spec_from_file_location("order_event_bridge", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_status_update_event_maps_into_order_row():
    row = module.event_payload_to_order_row("status_update", {
        "order_id": "43e14cbd",
        "status": "submitted",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "account": "sinopac_01",
        "broker_id": "sinopac",
    })
    assert row["order_id"] == "43e14cbd"
    assert row["status"] == "submitted"
    assert row["verified"] is True


def test_cancel_requested_event_maps_to_cancelled():
    row = module.event_payload_to_order_row("cancel_requested", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
    })
    assert row["status"] == "cancelled"


def test_event_without_order_id_is_ignored():
    row = module.event_payload_to_order_row("status_update", {"status": "submitted"})
    assert row is None
