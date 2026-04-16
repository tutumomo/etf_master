from pathlib import Path
import importlib.util
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/fills_ledger.py")
spec = importlib.util.spec_from_file_location("fills_ledger", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_save_and_load_fills_ledger_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "fills_ledger.json"
        rows = [{
            "order_id": "pf-001",
            "symbol": "00922",
            "filled_quantity": 300,
            "price": 27.45,
            "status": "partial_filled",
            "source_type": "broker_callback",
            "observed_at": "2026-04-03T09:01:09+08:00",
        }]
        module.save_fills_ledger(path, rows)
        payload = module.load_fills_ledger(path)
        assert payload["fills"][0]["order_id"] == "pf-001"
        assert payload["fills"][0]["filled_quantity"] == 300
