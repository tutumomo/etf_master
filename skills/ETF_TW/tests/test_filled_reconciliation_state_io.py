from pathlib import Path
import importlib.util
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/filled_reconciliation.py")
spec = importlib.util.spec_from_file_location("filled_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_save_and_load_reconciliation_report_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "filled_reconciliation.json"
        report = {
            "ok": False,
            "unreconciled_symbols": ["00922"],
            "unreconciled_count": 1,
            "source": "filled_reconciliation",
        }
        module.save_reconciliation_report(path, report)
        loaded = module.load_reconciliation_report(path)
        assert loaded["ok"] is False
        assert loaded["unreconciled_symbols"] == ["00922"]
