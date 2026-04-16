from pathlib import Path
import json

INTEL_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/market_intelligence.json")
EXPECTED = ["0050", "00878", "006208", "0056", "00922", "00679B"]


def test_market_intelligence_contains_expected_watch_symbols():
    payload = json.loads(INTEL_PATH.read_text(encoding="utf-8").replace("NaN", "null"))
    intel = payload.get("intelligence", {})
    for symbol in EXPECTED:
        assert symbol in intel, f"{symbol} missing from market_intelligence"


def test_market_intelligence_rows_have_history_and_rsi():
    payload = json.loads(INTEL_PATH.read_text(encoding="utf-8").replace("NaN", "null"))
    intel = payload.get("intelligence", {})
    for symbol in EXPECTED:
        row = intel[symbol]
        assert isinstance(row.get("history_30d"), list)
        assert len(row.get("history_30d", [])) >= 20
        assert row.get("rsi") is not None
