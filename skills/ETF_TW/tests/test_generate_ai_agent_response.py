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


def test_generate_ai_agent_response_from_request_writes_agent_source_payload():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-agent-101",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "elevated"},
                "market_intelligence": {"intelligence": {"0050": {"rsi": 53}, "00679B": {"rsi": 42}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name="ETF_Master")
        assert payload["source"] == "ai_agent"
        assert payload["agent"]["name"] == "ETF_Master"
        assert payload["review"]["status"] == "pending"
        assert payload["request_id"] == "req-agent-101"

        written = json.loads((state_dir / "ai_decision_response.json").read_text(encoding="utf-8"))
        assert written["source"] == "ai_agent"
        assert written["review"]["status"] == "pending"


def test_generate_ai_agent_response_keeps_reasoning_summary():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-agent-102",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "逢低觀察"},
                "market_context_taiwan": {"risk_temperature": "elevated"},
                "market_event_context": {"global_risk_level": "high"},
                "market_intelligence": {"intelligence": {"00940": {"rsi": 40}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name="ETF_Master")
        assert payload["reasoning"]["market_context_summary"] != ""
        assert payload["decision"]["strategy_alignment"] == "核心累積 / 逢低觀察"
