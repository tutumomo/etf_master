from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/dashboard_health.py")
spec = importlib.util.spec_from_file_location("dashboard_health", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def classify_freshness_stub(ts):
    return {"level": "good", "label": "fresh"} if ts else {"level": "bad", "label": "missing"}


def test_build_health_summary_payload_merges_reconciliation_warnings_and_intelligence():
    payload = module.build_health_summary_payload(
        market_event_context={"updated_at": "2026-04-03T01:00:00+08:00"},
        market_context_taiwan={"updated_at": "2026-04-03T01:00:00+08:00"},
        major_event_flag={"checked_at": "2026-04-03T01:00:00+08:00"},
        decision_quality={"evaluated_at": "2026-04-03T01:00:00+08:00"},
        auto_trade_state={"last_scan_at": "2026-04-03T01:00:00+08:00"},
        market_intelligence={
            "updated_at": "2026-04-03T01:00:00+08:00",
            "intelligence": {
                "0050": {"history_30d": [{}] * 30, "rsi": 50.0}
            }
        },
        reconciliation_warnings=["未成交委託尚未進入持倉：00922"],
        classify_freshness=classify_freshness_stub,
    )
    assert payload["intelligence_ready_count"] == 1
    assert "未成交委託尚未進入持倉：00922" in payload["warnings"]
    assert payload["health_summary"] == "需注意"
