from pathlib import Path
import importlib.util
import sys
from datetime import datetime

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/market_calendar_tw.py")
spec = importlib.util.spec_from_file_location("market_calendar_tw", MODULE_PATH)
module = importlib.util.module_from_spec(spec)


def test_fallback_to_weekday_time_when_calendar_missing_date():
    spec.loader.exec_module(module)
    calendar = {"dates": {}}
    result = module.get_today_market_status(
        now=datetime.fromisoformat("2026-04-07T10:00:00+08:00"),
        calendar_payload=calendar,
    )
    assert result["source"] == "weekday_time_fallback"
    assert result["is_open"] is True
