from pathlib import Path
import json
import tempfile
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
spec = importlib.util.spec_from_file_location("orders_open_state", MODULE_PATH)
orders_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orders_module)


def test_partial_filled_order_must_remain_only_in_orders_open_semantics():
    rows = orders_module.merge_open_orders([], {
        "order_id": "pf-001",
        "symbol": "00922",
        "action": "buy",
        "status": "partial_filled",
        "filled_quantity": 300,
        "remaining_quantity": 700,
        "price": 27.45,
        "source_type": "broker_callback",
    })
    assert len(rows) == 1
    assert rows[0]["status"] == "partial_filled"
    assert rows[0]["filled_quantity"] == 300
    assert rows[0]["remaining_quantity"] == 700


def test_partial_filled_order_should_not_imply_positions_payload_change():
    positions_payload = {
        "positions": [],
        "source": "live_broker",
    }
    open_rows = orders_module.merge_open_orders([], {
        "order_id": "pf-001",
        "symbol": "00922",
        "action": "buy",
        "status": "partial_filled",
        "filled_quantity": 300,
        "remaining_quantity": 700,
        "price": 27.45,
        "source_type": "broker_callback",
    })
    assert positions_payload["positions"] == []
    assert open_rows[0]["symbol"] == "00922"
