from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_health_summary_includes_reconciliation_warnings_field():
    body = module.overview_api()
    assert "decision_engine_health" in body
    assert "warnings" in body["decision_engine_health"]
    assert isinstance(body["decision_engine_health"]["warnings"], list)
