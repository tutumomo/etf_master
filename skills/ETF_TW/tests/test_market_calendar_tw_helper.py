from pathlib import Path
import importlib.util
import sys
from datetime import datetime

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/market_calendar_tw.py")
spec = importlib.util.spec_from_file_location("market_calendar_tw", MODULE_PATH)
module = importlib.util.module_from_spec(spec)


def test_holiday_calendar_should_mark_market_closed():
    spec.loader.exec_module(module)
    calendar = {
        "dates": {
            "2026-04-03": {
                "is_open": False,
                "session": "holiday_closed",
                "reason": "清明連假休市"
            }
        }
    }
    result = module.get_today_market_status(
        now=datetime.fromisoformat("2026-04-03T10:00:00+08:00"),
        calendar_payload=calendar,
    )
    assert result["is_open"] is False
    assert result["session"] == "holiday_closed"


def test_regular_trading_day_during_session_should_mark_open():
    spec.loader.exec_module(module)
    calendar = {
        "dates": {
            "2026-04-06": {
                "is_open": True,
                "session": "trading_day",
                "reason": "正常開市"
            }
        }
    }
    result = module.get_today_market_status(
        now=datetime.fromisoformat("2026-04-06T10:00:00+08:00"),
        calendar_payload=calendar,
    )
    assert result["is_open"] is True
    assert result["session"] == "trading_day"
