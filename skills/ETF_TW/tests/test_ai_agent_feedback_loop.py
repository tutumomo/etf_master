from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_agent_response.py")
spec = importlib.util.spec_from_file_location("generate_ai_agent_response", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_agent_response_lowers_confidence_when_recent_notes_show_superseded_pattern():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-feedback-001",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "逢低觀察"},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00940": {"rsi": 40}}},
                "decision_memory_context": {
                    "recent_review_count": 3,
                    "recent_outcome_count": 3,
                    "recent_reflection_count": 3,
                    "memory_notes": [
                        {"request_id": "a", "reflection_note": "最近常被新版建議取代", "review_status": "superseded", "outcome_status": "reviewed"},
                        {"request_id": "b", "reflection_note": "同型建議不夠穩定", "review_status": "superseded", "outcome_status": "reviewed"}
                    ]
                }
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name="ETF_Master")
        assert payload["decision"]["confidence"] == "low"
        assert "最近反思顯示此類建議穩定度不足" in payload["decision"]["summary"]


def test_agent_response_can_keep_or_raise_confidence_when_recent_notes_positive():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-feedback-002",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00679B": {"rsi": 41}}},
                "decision_memory_context": {
                    "recent_review_count": 2,
                    "recent_outcome_count": 2,
                    "recent_reflection_count": 2,
                    "memory_notes": [
                        {"request_id": "c", "reflection_note": "這類建議可保留", "review_status": "reviewed", "outcome_status": "reviewed"}
                    ]
                }
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name="ETF_Master")
        assert payload["decision"]["confidence"] in {"medium", "high"}
        assert payload["reasoning"]["risk_context_summary"] != ""
