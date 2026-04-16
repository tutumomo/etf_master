from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/dashboard_health.py")
spec = importlib.util.spec_from_file_location("dashboard_health", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def classify_ok(_):
    return {"level": "ok", "label": "ok"}


def test_health_summary_can_merge_market_calendar_warning():
    payload = module.build_health_summary_payload(
        market_event_context={"updated_at": "2026-04-03T09:00:00+08:00"},
        market_context_taiwan={"updated_at": "2026-04-03T09:00:00+08:00"},
        major_event_flag={"checked_at": "2026-04-03T09:00:00+08:00"},
        decision_quality={"evaluated_at": "2026-04-03T09:00:00+08:00"},
        auto_trade_state={"last_scan_at": "2026-04-03T09:00:00+08:00"},
        market_intelligence={"updated_at": "2026-04-03T09:00:00+08:00", "intelligence": {}},
        reconciliation_warnings=["market_calendar: holiday_closed 與 weekday 判斷不一致"],
        classify_freshness=classify_ok,
    )
    assert "market_calendar: holiday_closed 與 weekday 判斷不一致" in payload["warnings"]
