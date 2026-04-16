from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_agent_summary.py")
spec = importlib.util.spec_from_file_location("sync_agent_summary", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_watchlist_brief_uses_canonical_symbols_only():
    payload = {
        "items": [
            {"symbol": "0050.TW"},
            {"symbol": "0050"},
            {"symbol": "00679B.TWO"},
        ]
    }
    brief = module.build_watchlist_brief(payload)
    assert ".TW" not in brief
    assert ".TWO" not in brief
    assert brief == "目前關注標的：0050、00679B。"


def test_tape_brief_deduplicates_provider_variant_intelligence_keys():
    tape = {
        "market_bias": "risk-off",
        "tape_summary": "空方佔優；盤面回撤明顯，需強化防禦布局。"
    }
    intel = {
        "intelligence": {
            "0050": {"rsi": 47, "last_price": 73.95, "sma20": 75.48},
            "0050.TW": {"rsi": 47, "last_price": 73.95, "sma20": 75.48},
            "00878": {"rsi": 45, "last_price": 22.03, "sma20": 22.28},
        }
    }
    brief = module.build_tape_brief(tape, intel)
    assert brief.count("0050(") == 1
    assert ".TW" not in brief
    assert "目前市場情緒：risk-off。" in brief
