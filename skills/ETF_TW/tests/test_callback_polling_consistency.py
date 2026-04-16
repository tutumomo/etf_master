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


def test_callback_then_polling_on_same_order_id_keeps_single_row():
    callback_row = callback_module.event_payload_to_order_row("order_submitted", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "broker_id": "sinopac",
        "account": "sinopac_01",
    })
    rows = orders_module.merge_open_orders([], callback_row)

    polling_row = {
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
    rows = orders_module.merge_open_orders(rows, polling_row)
    assert len(rows) == 1
    assert rows[0]["order_id"] == "43e14cbd"
    assert rows[0]["status"] == "submitted"


def test_callback_terminal_update_and_polling_terminal_update_both_cleanup_order():
    rows = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
        "verified": True,
    }]
    callback_terminal = callback_module.event_payload_to_order_row("order_filled", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
    })
    rows = orders_module.merge_open_orders(rows, callback_terminal)
    assert rows == []
