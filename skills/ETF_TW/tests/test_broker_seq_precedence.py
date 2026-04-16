from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_higher_broker_seq_should_win_when_time_and_status_same():
    existing = [{
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_callback",
        "broker_seq": 10,
    }]
    incoming = {
        "order_id": "abc",
        "status": "submitted",
        "symbol": "00922",
        "event_time": "2026-04-03T09:01:08+08:00",
        "source_type": "broker_callback",
        "broker_seq": 12,
    }
    rows = orders_module.merge_open_orders(existing, incoming)
    assert rows[0]["broker_seq"] == 12
