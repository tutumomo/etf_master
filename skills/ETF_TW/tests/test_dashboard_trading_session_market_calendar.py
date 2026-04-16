from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_resolve_market_session_open_prefers_market_calendar_closed():
    result = module.resolve_market_session_open(
        auto_trade_state={"market_session_open": True},
        market_calendar_status={"is_open": False, "session": "holiday_closed", "source": "market_calendar_tw"},
    )
    assert result["market_session_open"] is False
    assert result["market_session_label"] == "休市中"
    assert result["source"] == "market_calendar_tw"


def test_resolve_market_session_open_uses_fallback_when_calendar_missing():
    result = module.resolve_market_session_open(
        auto_trade_state={"market_session_open": True},
        market_calendar_status={"is_open": True, "session": "trading_day", "source": "weekday_time_fallback"},
    )
    assert result["market_session_open"] is True
    assert result["market_session_label"] == "交易時段中"
