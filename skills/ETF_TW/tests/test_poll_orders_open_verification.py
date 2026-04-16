from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
spec = importlib.util.spec_from_file_location("orders_open_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_polling_verified_row_preserves_verification_metadata():
    row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "submitted",
    }
    merged = module.merge_open_orders([], row)
    assert len(merged) == 1
    assert merged[0]["verified"] is True
    assert merged[0]["broker_order_id"] == "43e14cbd"
    assert merged[0]["broker_status"] == "submitted"


def test_polling_terminal_verified_row_is_removed_from_open_list():
    row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "filled",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "filled",
    }
    merged = module.merge_open_orders([], row)
    assert merged == []
