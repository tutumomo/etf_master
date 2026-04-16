from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/fills_ledger.py")
spec = importlib.util.spec_from_file_location("fills_ledger", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_merge_fill_facts_dedupes_same_order_and_keeps_latest_filled_quantity():
    existing = [{
        "order_id": "pf-001",
        "symbol": "00922",
        "filled_quantity": 300,
        "price": 27.45,
        "status": "partial_filled",
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:01:09+08:00",
    }]
    incoming = {
        "order_id": "pf-001",
        "symbol": "00922",
        "filled_quantity": 500,
        "price": 27.45,
        "status": "partial_filled",
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:03:09+08:00",
    }
    rows = module.merge_fill_facts(existing, incoming)
    assert len(rows) == 1
    assert rows[0]["filled_quantity"] == 500


def test_merge_fill_facts_preserves_multiple_orders():
    existing = [{
        "order_id": "pf-001",
        "symbol": "00922",
        "filled_quantity": 300,
        "price": 27.45,
        "status": "partial_filled",
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:01:09+08:00",
    }]
    incoming = {
        "order_id": "pf-002",
        "symbol": "0050",
        "filled_quantity": 100,
        "price": 180.0,
        "status": "partial_filled",
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:03:09+08:00",
    }
    rows = module.merge_fill_facts(existing, incoming)
    assert len(rows) == 2
