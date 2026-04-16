from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_ohlcv_history.py")
spec = importlib.util.spec_from_file_location("sync_ohlcv_history", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_should_preserve_existing_payload_when_new_intelligence_empty_and_symbols_exist():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "market_intelligence.json"
        existing = {
            "updated_at": "2026-04-03T10:00:00+08:00",
            "intelligence": {"0050": {"symbol": "0050", "rsi": 55}},
            "source": "sync_ohlcv_history_pro"
        }
        path.write_text(json.dumps(existing), encoding="utf-8")
        payload = module.build_market_intelligence_payload(
            symbols=["0050", "006208"],
            intelligence={},
            existing_payload=existing,
        )
        assert payload["intelligence"] == existing["intelligence"]
        assert payload["_warning"] == "market_intelligence: tracked symbols exist but intelligence payload is empty"
        assert payload["_stale_fallback"] is True


def test_append_skip_reason_records_symbol_and_reason():
    errors = []
    module.append_skip_reason(errors, "006208", "no_history")
    module.append_skip_reason(errors, "0050", "indicator_calc_failed")
    assert errors == [
        {"symbol": "006208", "reason": "no_history"},
        {"symbol": "0050", "reason": "indicator_calc_failed"},
    ]
