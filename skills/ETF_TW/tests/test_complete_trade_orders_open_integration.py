from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
spec = importlib.util.spec_from_file_location("orders_open_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_submit_style_integration_adds_order_to_open_list():
    rows = []
    submitted_row = {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
        "account": "sinopac_01",
        "broker_id": "sinopac",
    }
    merged = module.merge_open_orders(rows, submitted_row)
    assert len(merged) == 1
    assert merged[0]["order_id"] == "43e14cbd"
    assert merged[0]["status"] == "submitted"
    assert merged[0]["account"] == "sinopac_01"


def test_submit_style_terminal_update_removes_open_order():
    rows = [{
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
        "mode": "live",
        "status": "submitted",
        "source": "live_broker",
        "account": "sinopac_01",
        "broker_id": "sinopac",
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
        "account": "sinopac_01",
        "broker_id": "sinopac",
    }
    merged = module.merge_open_orders(rows, terminal_row)
    assert merged == []
