from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_windows.py")
spec = importlib.util.spec_from_file_location("layered_review_windows", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_get_layered_review_windows_returns_early_short_mid():
    windows = module.get_layered_review_windows()
    names = [w['name'] for w in windows]
    assert names == ['early_review', 'short_review', 'mid_review']
    assert windows[0]['offset_trading_days'] == 1
    assert windows[1]['offset_trading_days'] in {3, 5}
    assert windows[2]['offset_trading_days'] >= 10
