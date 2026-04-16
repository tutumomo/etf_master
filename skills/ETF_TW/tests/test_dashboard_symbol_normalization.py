from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_dashboard_normalize_symbol_strips_provider_suffixes():
    assert module.normalize_symbol("0050.TW") == "0050"
    assert module.normalize_symbol("00679B.TWO") == "00679B"
    assert module.normalize_symbol("00878") == "00878"
