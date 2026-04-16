from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_filled_quantity_must_not_move_backward():
    existing = [{
        "order_id": "abc",
        "status": "partial_filled",
        "symbol": "00922",
        "quantity": 400,
        "filled_quantity": 400,
        "remaining_quantity": 600,
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_callback",
    }]
    incoming = {
        "order_id": "abc",
        "status": "partial_filled",
        "symbol": "00922",
        "quantity": 200,
        "filled_quantity": 200,
        "remaining_quantity": 800,
        "event_time": "2026-04-03T09:01:09+08:00",
        "source_type": "broker_callback",
    }
    rows = orders_module.merge_open_orders(existing, incoming)
    assert rows[0]["filled_quantity"] == 400
    assert rows[0]["remaining_quantity"] == 600


def test_remaining_quantity_should_follow_total_minus_filled_when_possible():
    existing = []
    incoming = {
        "order_id": "abc",
        "status": "partial_filled",
        "symbol": "00922",
        "quantity": 1000,
        "total_quantity": 1000,
        "filled_quantity": 300,
        "remaining_quantity": 999,
        "event_time": "2026-04-03T09:01:09+08:00",
        "source_type": "broker_callback",
    }
    rows = orders_module.merge_open_orders(existing, incoming)
    assert rows[0]["filled_quantity"] == 300
    assert rows[0]["remaining_quantity"] == 700
