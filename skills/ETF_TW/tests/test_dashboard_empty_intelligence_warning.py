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


def test_health_summary_warns_when_market_intelligence_payload_is_empty():
    payload = module.build_health_summary_payload(
        market_event_context={"updated_at": "2026-04-03T10:00:00+08:00"},
        market_context_taiwan={"updated_at": "2026-04-03T10:00:00+08:00"},
        major_event_flag={"checked_at": "2026-04-03T10:00:00+08:00"},
        decision_quality={"evaluated_at": "2026-04-03T10:00:00+08:00"},
        auto_trade_state={"last_scan_at": "2026-04-03T10:00:00+08:00"},
        market_intelligence={"updated_at": "2026-04-03T10:00:00+08:00", "intelligence": {}},
        reconciliation_warnings=[],
        classify_freshness=classify_ok,
    )
    assert "market_intelligence: 無可用技術指標資料" in payload["warnings"]
