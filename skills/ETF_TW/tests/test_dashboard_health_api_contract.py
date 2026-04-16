from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_health_api_exposes_summary_and_reconciliation():
    body = module.health()
    assert "ok" in body
    assert "health_summary" in body
    assert "warnings" in body
    assert "state_reconciliation" in body
    assert isinstance(body["warnings"], list)
    assert isinstance(body["state_reconciliation"], dict)
