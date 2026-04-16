from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_ohlcv_history.py")
spec = importlib.util.spec_from_file_location("sync_ohlcv_history", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_empty_intelligence_warning_when_symbols_exist():
    warning = module.build_empty_intelligence_warning(["0050", "006208"], {})
    assert warning == "market_intelligence: tracked symbols exist but intelligence payload is empty"


def test_build_empty_intelligence_warning_returns_none_when_symbols_missing():
    warning = module.build_empty_intelligence_warning([], {})
    assert warning is None
