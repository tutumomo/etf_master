from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_partial_fill_keeps_order_open_with_remaining_quantity():
    existing = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 1000,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "submitted",
    }]

    partial_update = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 400,
        "remaining_quantity": 600,
        "filled_quantity": 400,
        "price": 27.45,
        "mode": "live",
        "status": "partial_filled",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "partial_filled",
    }

    rows = orders_module.merge_open_orders(existing, partial_update)
    assert len(rows) == 1
    row = rows[0]
    assert row["order_id"] == "43e14cbd"
    assert row["status"] == "partial_filled"
    assert row["remaining_quantity"] == 600
    assert row["filled_quantity"] == 400


def test_partial_fill_must_not_be_cleaned_up_as_terminal():
    partial_update = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 400,
        "remaining_quantity": 600,
        "filled_quantity": 400,
        "price": 27.45,
        "mode": "live",
        "status": "partial_filled",
        "source": "live_broker",
        "verified": True,
    }

    rows = orders_module.merge_open_orders([], partial_update)
    assert len(rows) == 1
    assert rows[0]["status"] == "partial_filled"
