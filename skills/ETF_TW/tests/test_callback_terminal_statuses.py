from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)

CALLBACK_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_event_bridge.py")
callback_spec = importlib.util.spec_from_file_location("order_event_bridge", CALLBACK_MODULE_PATH)
callback_module = importlib.util.module_from_spec(callback_spec)
callback_spec.loader.exec_module(callback_module)

BASE_ROW = {
    "order_id": "43e14cbd",
    "symbol": "00922",
    "action": "buy",
    "quantity": 50,
    "price": 27.45,
    "mode": "live",
    "status": "submitted",
    "source": "live_broker",
    "verified": True,
}


def test_order_cancelled_event_cleans_open_order():
    rows = [dict(BASE_ROW)]
    row = callback_module.event_payload_to_order_row("order_cancelled", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
    })
    assert orders_module.merge_open_orders(rows, row) == []


def test_order_rejected_event_cleans_open_order():
    rows = [dict(BASE_ROW)]
    row = callback_module.event_payload_to_order_row("order_rejected", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
    })
    assert orders_module.merge_open_orders(rows, row) == []


def test_cancel_requested_event_also_cleans_open_order():
    rows = [dict(BASE_ROW)]
    row = callback_module.event_payload_to_order_row("cancel_requested", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
    })
    assert orders_module.merge_open_orders(rows, row) == []
