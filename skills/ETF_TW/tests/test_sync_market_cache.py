from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_market_cache.py")
spec = importlib.util.spec_from_file_location("sync_market_cache", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_quote_entry_has_required_fields():
    entry = module.build_quote_entry("0050", 75.0)
    assert entry["symbol"] == "0050"
    assert entry["current_price"] == 75.0
    assert "updated_at" in entry


def test_canonicalize_symbol_strips_tw_suffixes():
    assert module.canonicalize_symbol("0050.TW") == "0050"
    assert module.canonicalize_symbol("00679B.TWO") == "00679B"
    assert module.canonicalize_symbol("00878") == "00878"


def test_build_candidate_symbols_uses_canonical_symbol_mapping():
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
    assert module.build_candidate_symbols("00679B.TWO", mappings) == ["00679B.TWO", "00679B.TW"]
    assert module.build_candidate_symbols("0050.TW", mappings) == ["0050.TW"]
