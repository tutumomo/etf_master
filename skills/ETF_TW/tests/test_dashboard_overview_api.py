from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_api_returns_expected_keys():
    body = module.overview_api()
    for key in ["account", "positions", "strategy", "trading_mode", "market_cache", "position_rows"]:
        assert key in body
