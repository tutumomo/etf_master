import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

MODULE_PATH = ROOT / "scripts" / "sync_orders_open_state.py"
spec = importlib.util.spec_from_file_location("sync_orders_open_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DealRecord:
    def __init__(self, record):
        self.record = record


def test_deal_records_remove_matching_filled_order_from_open_list():
    open_orders = [{
        "order_id": "preview-001",
        "broker_order_id": "Y0GU9",
        "symbol": "006208",
        "action": "buy",
        "quantity": 6,
        "price": 212.1,
        "status": "submitted",
        "source": "live_broker",
        "source_type": "live_submit_sop",
        "verified": True,
    }]
    records = [
        DealRecord({
            "trade_id": "59df36db",
            "ordno": "Y0GU9",
            "action": "Buy",
            "code": "006208",
            "price": 211.55,
            "quantity": 6,
        })
    ]

    terminal_rows = module._deal_rows_from_records(open_orders, records)
    merged = module._merge_terminal_rows(open_orders, terminal_rows)

    assert terminal_rows[0]["status"] == "filled"
    assert terminal_rows[0]["broker_status"] == "filled"
    assert terminal_rows[0]["filled_quantity"] == 6
    assert terminal_rows[0]["filled_price"] == 211.55
    assert merged == []


def test_deal_records_ignore_unrelated_ordno():
    open_orders = [{
        "order_id": "preview-001",
        "broker_order_id": "Y0GU9",
        "symbol": "006208",
        "action": "buy",
        "quantity": 6,
        "price": 212.1,
        "status": "submitted",
    }]
    records = [DealRecord({"ordno": "OTHER", "action": "Buy", "code": "006208", "quantity": 6})]

    assert module._deal_rows_from_records(open_orders, records) == []
