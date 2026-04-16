from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_OPEN_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_OPEN_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_polling_style_update_keeps_submitted_order_open():
    rows = []
    polled_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
    }
    merged = orders_module.merge_open_orders(rows, polled_row)
    assert len(merged) == 1
    assert merged[0]["status"] == "submitted"


def test_polling_style_update_removes_terminal_order_from_open_list():
    rows = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
    }]
    terminal_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "filled",
        "source": "live_broker",
    }
    merged = orders_module.merge_open_orders(rows, terminal_row)
    assert merged == []
