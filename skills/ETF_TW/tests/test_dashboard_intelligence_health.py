from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_health_exposes_intelligence_readiness():
    body = module.overview_api()
    health = body["decision_engine_health"]
    assert "last_intelligence_refresh" in health
    assert "intelligence_ready_count" in health
    assert isinstance(health["intelligence_ready_count"], int)
