from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/fills_ledger.py")
spec = importlib.util.spec_from_file_location("fills_ledger", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_fill_fact_row_has_minimum_contract():
    row = module.build_fill_fact_row({
        "order_id": "pf-001",
        "symbol": "00922",
        "action": "buy",
        "status": "partial_filled",
        "filled_quantity": 300,
        "remaining_quantity": 700,
        "price": 27.45,
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:01:09+08:00",
    })
    assert row["order_id"] == "pf-001"
    assert row["symbol"] == "00922"
    assert row["filled_quantity"] == 300
    assert row["price"] == 27.45
    assert row["source_type"] == "broker_callback"
    assert row["observed_at"] == "2026-04-03T09:01:09+08:00"


def test_partial_filled_event_should_be_recordable_in_fills_ledger_payload():
    row = module.build_fill_fact_row({
        "order_id": "pf-001",
        "symbol": "00922",
        "action": "buy",
        "status": "partial_filled",
        "filled_quantity": 300,
        "remaining_quantity": 700,
        "price": 27.45,
        "source_type": "broker_callback",
        "observed_at": "2026-04-03T09:01:09+08:00",
    })
    payload = module.build_fills_ledger_payload([row], source="fill_facts")
    assert payload["source"] == "fill_facts"
    assert len(payload["fills"]) == 1
    assert payload["fills"][0]["status"] == "partial_filled"
