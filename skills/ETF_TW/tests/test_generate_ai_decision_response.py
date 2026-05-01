from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_decision_response.py")
spec = importlib.util.spec_from_file_location("generate_ai_decision_response", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_response_payload_from_request_writes_response_file():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-001",
            "requested_by": "dashboard",
            "mode": "preview_only",
            "context_version": "核心累積::收益再投資",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
                "positions": {"positions": []},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00679B": {"rsi": 48}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")

        payload = module.generate_response_payload_from_state_dir(state_dir)
        assert payload["request_id"] == "req-001"
        assert payload["source"] == "ai_decision_bridge"
        assert payload["decision"]["action"] in {"hold", "preview_buy", "watch_only"}

        written = json.loads((state_dir / "ai_decision_response.json").read_text(encoding="utf-8"))
        assert written["request_id"] == "req-001"
        assert "summary" in written["decision"]


def test_generate_response_payload_marks_preview_candidate_when_intelligence_exists():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-002",
            "requested_by": "system",
            "mode": "decision_only",
            "context_version": "核心累積::逢低觀察",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "逢低觀察"},
                "positions": {"positions": []},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"0050": {"rsi": 52}, "00679B": {"rsi": 44}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_response_payload_from_state_dir(state_dir)
        assert payload["candidate"]["symbol"] in {"0050", "00679B"}
        assert payload["decision"]["confidence"] in {"medium", "high"}


def test_ai_bridge_uses_watchlist_context_strategy_weights():
    request_payload = {
        "request_id": "req-watchlist",
        "inputs": {
            "strategy": {"base_strategy": "防守保守", "scenario_overlay": "高波動警戒"},
            "market_context_taiwan": {"risk_temperature": "elevated"},
            "market_event_context": {"global_risk_level": "elevated"},
            "watchlist_context": {
                "items": [
                    {
                        "symbol": "00939",
                        "name": "統一台灣高息動能",
                        "watchlist_group": "smart_beta",
                        "is_held": False,
                        "market_metrics": {"rsi": 43, "momentum_20d": 10, "sharpe_30d": 2.3},
                    },
                    {
                        "symbol": "00720B",
                        "name": "元大投資級公司債",
                        "watchlist_group": "defensive",
                        "asset_class": "bond",
                        "is_held": False,
                        "market_metrics": {"rsi": 48, "momentum_20d": -1, "sharpe_30d": 0.4},
                    },
                ]
            },
        },
    }

    candidate, summary, action, confidence = module._pick_candidate(request_payload)

    assert action == "preview_buy"
    assert candidate["symbol"] == "00720B"
    assert "防守保守" in candidate["risk_note"]
    assert confidence in {"medium", "high"}


def test_ai_bridge_income_strategy_does_not_default_to_defensive_etf():
    request_payload = {
        "request_id": "req-income",
        "inputs": {
            "strategy": {"base_strategy": "收益優先", "scenario_overlay": "收益再投資"},
            "market_context_taiwan": {"risk_temperature": "elevated"},
            "market_event_context": {"global_risk_level": "elevated"},
            "watchlist_context": {
                "items": [
                    {
                        "symbol": "00720B",
                        "name": "元大投資級公司債",
                        "watchlist_group": "defensive",
                        "asset_class": "bond",
                        "market_metrics": {"rsi": 43, "momentum_20d": 1, "sharpe_30d": 0.8},
                    },
                    {
                        "symbol": "00713",
                        "name": "元大台灣高息低波",
                        "watchlist_group": "income",
                        "market_metrics": {"rsi": 50, "momentum_20d": 2, "sharpe_30d": 1.2},
                    },
                ]
            },
        },
    }

    candidate, summary, action, confidence = module._pick_candidate(request_payload)

    assert candidate["symbol"] == "00713"
    assert candidate["group"] == "income"
    assert candidate["side"] == "watch"
    assert action == "watch_only"


def test_ai_bridge_observation_mode_does_not_create_preview():
    request_payload = {
        "request_id": "req-observe",
        "inputs": {
            "strategy": {"base_strategy": "觀察模式", "scenario_overlay": "無"},
            "watchlist_context": {"items": [{"symbol": "00939", "watchlist_group": "smart_beta"}]},
        },
    }

    candidate, summary, action, confidence = module._pick_candidate(request_payload)

    assert candidate == {}
    assert action == "watch_only"
    assert "觀察模式" in summary
