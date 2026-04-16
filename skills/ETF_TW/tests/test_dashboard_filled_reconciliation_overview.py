from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_api_exposes_filled_reconciliation_block():
    body = module.overview_api()
    assert "filled_reconciliation" in body
    assert isinstance(body["filled_reconciliation"], dict)
    assert "ok" in body["filled_reconciliation"]
    assert "unreconciled_symbols" in body["filled_reconciliation"]
