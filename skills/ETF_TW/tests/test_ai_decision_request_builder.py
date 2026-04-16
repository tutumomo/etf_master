from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_bridge.py")
spec = importlib.util.spec_from_file_location("ai_decision_bridge", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_ai_decision_request_from_state_prefers_positions_truth():
    payload = module.build_ai_decision_request_from_state(
        strategy={"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
        positions={"positions": [{"symbol": "0050", "quantity": 100}]},
        orders_open={"orders": []},
        fills_ledger={"fills": []},
        portfolio_snapshot={"holdings": [{"symbol": "0050", "quantity": 999}]},
        market_cache={"quotes": {"0050": {"current_price": 180}}},
        market_intelligence={"intelligence": {"0050": {"rsi": 55}}},
        intraday_tape_context={"market_bias": "neutral"},
        market_context_taiwan={"risk_temperature": "normal"},
        market_event_context={"global_risk_level": "elevated"},
        market_calendar_status={"is_open": False, "session": "holiday_closed"},
        reconciliation={"positions_vs_snapshot_match": False},
        requested_by="dashboard",
        mode="preview_only",
        context_version="ctx-test-001",
    )
    assert payload["requested_by"] == "dashboard"
    assert payload["mode"] == "preview_only"
    assert payload["inputs"]["positions"]["positions"][0]["quantity"] == 100
    assert payload["inputs"]["portfolio_snapshot"]["holdings"][0]["quantity"] == 999
    assert payload["inputs"]["market_calendar_status"]["session"] == "holiday_closed"


def test_build_ai_decision_request_from_state_includes_reconciliation_and_event_context():
    payload = module.build_ai_decision_request_from_state(
        strategy={},
        positions={},
        orders_open={"orders": [{"symbol": "00922"}]},
        fills_ledger={"fills": [{"symbol": "00922", "qty": 50}]},
        portfolio_snapshot={},
        market_cache={},
        market_intelligence={},
        intraday_tape_context={},
        market_context_taiwan={},
        market_event_context={"geo_political_risk": "high"},
        market_calendar_status={},
        reconciliation={"open_orders_not_in_positions": ["00922"]},
        requested_by="system",
        mode="decision_only",
        context_version="ctx-test-002",
    )
    assert payload["inputs"]["orders_open"]["orders"][0]["symbol"] == "00922"
    assert payload["inputs"]["fills_ledger"]["fills"][0]["symbol"] == "00922"
    assert payload["inputs"]["market_event_context"]["geo_political_risk"] == "high"
    assert payload["inputs"]["reconciliation"]["open_orders_not_in_positions"] == ["00922"]
