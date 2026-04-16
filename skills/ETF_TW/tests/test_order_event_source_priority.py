from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_callback_should_win_over_polling_when_status_and_time_equal():
    existing = [{
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_polling",
    }]
    incoming = {
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_callback",
    }
    rows = orders_module.merge_open_orders(existing, incoming)
    assert rows[0]["source_type"] == "broker_callback"


def test_polling_should_win_over_submit_response_when_status_and_time_equal():
    existing = [{
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "submit_response",
    }]
    incoming = {
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_polling",
    }
    rows = orders_module.merge_open_orders(existing, incoming)
    assert rows[0]["source_type"] == "broker_polling"
