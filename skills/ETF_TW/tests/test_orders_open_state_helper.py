from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
spec = importlib.util.spec_from_file_location("orders_open_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_merge_open_orders_adds_submitted_order():
    rows = []
    new_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "mode": "live",
        "status": "submitted",
    }
    merged = module.merge_open_orders(rows, new_row)
    assert len(merged) == 1
    assert merged[0]["order_id"] == "43e14cbd"
    assert merged[0]["status"] == "submitted"


def test_merge_open_orders_replaces_same_order_id():
    rows = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
    }]
    new_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "mode": "live",
        "status": "submitted",
        "ordno": "Y0E6D",
    }
    merged = module.merge_open_orders(rows, new_row)
    assert len(merged) == 1
    assert merged[0]["ordno"] == "Y0E6D"


def test_merge_open_orders_drops_terminal_status_rows():
    rows = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "mode": "live",
        "status": "submitted",
    }]
    new_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "mode": "live",
        "status": "filled",
    }
    merged = module.merge_open_orders(rows, new_row)
    assert merged == []
