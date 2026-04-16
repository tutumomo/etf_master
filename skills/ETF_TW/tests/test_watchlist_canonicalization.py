from pathlib import Path
import importlib.util
import json

SYNC_MARKET_CACHE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_market_cache.py")
CACHE_SPEC = importlib.util.spec_from_file_location("sync_market_cache", SYNC_MARKET_CACHE_PATH)
sync_market_cache = importlib.util.module_from_spec(CACHE_SPEC)
CACHE_SPEC.loader.exec_module(sync_market_cache)

SYNC_AGENT_SUMMARY_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_agent_summary.py")
SUMMARY_SPEC = importlib.util.spec_from_file_location("sync_agent_summary", SYNC_AGENT_SUMMARY_PATH)
sync_agent_summary = importlib.util.module_from_spec(SUMMARY_SPEC)
SUMMARY_SPEC.loader.exec_module(sync_agent_summary)


def test_canonicalize_symbol_normalizes_watchlist_variants():
    assert sync_market_cache.canonicalize_symbol("0050.TW") == "0050"
    assert sync_market_cache.canonicalize_symbol("00878.TW") == "00878"
    assert sync_market_cache.canonicalize_symbol("00679B.TWO") == "00679B"


def test_watchlist_brief_deduplicates_provider_variants():
    payload = {
        "items": [
            {"symbol": "0050"},
            {"symbol": "0050.TW"},
            {"symbol": "00878"},
            {"symbol": "00878.TW"},
            {"symbol": "00679B.TWO"},
        ]
    }
    brief = sync_agent_summary.build_watchlist_brief(payload)
    assert brief == "目前關注標的：0050、00878、00679B。"
