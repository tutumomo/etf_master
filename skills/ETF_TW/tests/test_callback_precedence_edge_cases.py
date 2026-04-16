from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


def test_terminal_status_must_not_be_overwritten_by_older_submitted_update():
    existing = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 1000,
        "price": 27.45,
        "mode": "live",
        "status": "filled",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "filled",
    }]

    older_update = {
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
    }

    rows = orders_module.merge_open_orders(existing, older_update)
    assert rows == []


def test_partial_fill_must_not_be_overwritten_by_plain_submitted_update():
    existing = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 400,
        "filled_quantity": 400,
        "remaining_quantity": 600,
        "price": 27.45,
        "mode": "live",
        "status": "partial_filled",
        "source": "live_broker",
        "verified": True,
        "broker_order_id": "43e14cbd",
        "broker_status": "partial_filled",
    }]

    older_update = {
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
    }

    rows = orders_module.merge_open_orders(existing, older_update)
    assert len(rows) == 1
    assert rows[0]["status"] == "partial_filled"
    assert rows[0]["remaining_quantity"] == 600
    assert rows[0]["filled_quantity"] == 400
