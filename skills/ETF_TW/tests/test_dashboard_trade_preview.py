import importlib.util
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
dashboard_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard_app)


def test_trade_preview_returns_preflight_payload():
    payload = dashboard_app.TradeRequest(
        symbol="0050",
        side="buy",
        quantity=1000,
        price=180.0,
    )

    result = dashboard_app.trade_preview(payload)

    assert result["ok"] is True
    assert result["symbol"] == "0050"
    assert result["estimated_total"] == 180000.0
    assert "pre_flight" in result
    assert "ok" in result["pre_flight"]
    assert "reason" in result["pre_flight"]


def test_trade_preview_uses_items_watchlist_for_strategy_alignment():
    payload = dashboard_app.TradeRequest(
        symbol="00878",
        side="buy",
        quantity=1000,
        price=20.0,
    )

    captured = {}

    def fake_check_order(order, context):
        captured["order"] = order
        captured["context"] = context
        return {"passed": True, "reason": "", "details": {}, "investment_score": 5, "score_breakdown": ["策略對齊 +2"]}

    def fake_safe_load_json(path, default=None):
        path_name = path.name
        if path_name == "market_context_taiwan.json":
            return {"market_regime": "balanced_bullish"}
        if path_name == "strategy_link.json":
            return {"base_strategy": "收益優先"}
        if path_name == "watchlist.json":
            return {"items": [{"symbol": "00878", "group": "income"}]}
        return default if default is not None else {}

    with patch.object(dashboard_app, "build_overview_model", return_value={"account": {"cash": 100000.0}, "positions": {"positions": []}}), \
         patch.object(dashboard_app, "safe_load_json", side_effect=fake_safe_load_json), \
         patch.object(dashboard_app.pre_flight, "check_order", side_effect=fake_check_order):
        dashboard_app.trade_preview(payload)

    assert captured["context"]["strategy_aligned"] is True
    assert captured["context"]["market_regime"] == "balanced_bullish"


def test_trade_preview_includes_ai_confidence_for_matching_symbol():
    payload = dashboard_app.TradeRequest(
        symbol="0050",
        side="buy",
        quantity=1000,
        price=180.0,
    )

    captured = {}

    def fake_check_order(order, context):
        captured["order"] = order
        return {
            "passed": True,
            "reason": "",
            "details": {},
            "investment_score": 4,
            "score_breakdown": ["AI信心:medium +1", "規模合理(0%<15%) +2", "市場bullish +1"],
        }

    def fake_safe_load_json(path, default=None):
        path_name = path.name
        if path_name == "market_context_taiwan.json":
            return {"market_regime": "balanced_bullish"}
        if path_name == "strategy_link.json":
            return {"base_strategy": "收益優先"}
        if path_name == "watchlist.json":
            return {"items": [{"symbol": "0050", "group": "core"}]}
        if path_name == "ai_decision_response.json":
            return {
                "stale": False,
                "decision": {"confidence": "medium"},
                "candidate": {"symbol": "0050"},
            }
        return default if default is not None else {}

    with patch.object(dashboard_app, "build_overview_model", return_value={"account": {"cash": 100000.0}, "positions": {"positions": []}}), \
         patch.object(dashboard_app, "safe_load_json", side_effect=fake_safe_load_json), \
         patch.object(dashboard_app.pre_flight, "check_order", side_effect=fake_check_order):
        result = dashboard_app.trade_preview(payload)

    assert captured["order"]["ai_confidence"] == "medium"
    assert result["pre_flight"]["ai_confidence"] == "medium"
    assert result["pre_flight"]["ai_confidence_source"] == "ai_decision_response"


def test_trade_preview_falls_back_to_heuristic_ai_confidence_for_other_symbols():
    payload = dashboard_app.TradeRequest(
        symbol="00878",
        side="buy",
        quantity=1000,
        price=20.0,
    )

    captured = {}

    def fake_check_order(order, context):
        captured["order"] = order
        return {
            "passed": True,
            "reason": "",
            "details": {},
            "investment_score": 6,
            "score_breakdown": ["AI信心:high +3", "策略對齊 +2", "市場bullish +1"],
        }

    def fake_safe_load_json(path, default=None):
        path_name = path.name
        if path_name == "market_context_taiwan.json":
            return {"market_regime": "balanced_bullish"}
        if path_name == "strategy_link.json":
            return {"base_strategy": "收益優先"}
        if path_name == "watchlist.json":
            return {"items": [{"symbol": "00878", "group": "income"}]}
        if path_name == "ai_decision_response.json":
            return {
                "stale": False,
                "decision": {"confidence": "medium"},
                "candidate": {"symbol": "0050"},
            }
        if path_name == "ai_decision_request.json":
            return {
                "inputs": {
                    "market_intelligence": {
                        "intelligence": {
                            "00878": {
                                "rsi": 56.0,
                                "momentum_20d": 10.0,
                                "sharpe_30d": 3.2,
                                "macd": 0.5,
                                "macd_signal": 0.2,
                                "sma5": 24.0,
                                "sma20": 23.0,
                            }
                        }
                    }
                }
            }
        return default if default is not None else {}

    with patch.object(dashboard_app, "build_overview_model", return_value={"account": {"cash": 100000.0}, "positions": {"positions": []}}), \
         patch.object(dashboard_app, "safe_load_json", side_effect=fake_safe_load_json), \
         patch.object(dashboard_app.pre_flight, "check_order", side_effect=fake_check_order):
        result = dashboard_app.trade_preview(payload)

    assert captured["order"]["ai_confidence"] == "high"
    assert result["pre_flight"]["ai_confidence"] == "high"
    assert result["pre_flight"]["ai_confidence_source"] == "ai_bridge_heuristic"
