from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_ohlcv_history.py")
spec = importlib.util.spec_from_file_location("sync_ohlcv_history", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_candidate_symbols_respects_mapping_registry():
    mappings = {
        "symbols": {
            "00679B": {
                "yfinance_candidates": ["00679B.TWO", "00679B.TW"]
            }
        },
        "defaults": {
            "yfinance_candidates": ["{symbol}.TW"]
        }
    }
    assert module.build_candidate_symbols("00679B", mappings) == ["00679B.TWO", "00679B.TW"]
    assert module.build_candidate_symbols("0050", mappings) == ["0050.TW"]
