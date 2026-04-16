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


def test_agent_response_respects_quality_hook_lower_bias():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-qh-001",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "逢低觀察"},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00940": {"rsi": 40}}},
                "decision_memory_context": {
                    "memory_notes": [],
                    "quality_hooks": {"confidence_bias": "lower", "quality_summary": "recent preview_buy: reviewed=0, superseded=3"}
                }
            }
        }
        (state_dir / 'ai_decision_request.json').write_text(json.dumps(request_payload), encoding='utf-8')
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name='ETF_Master')
        assert payload['decision']['confidence'] == 'low'
        assert 'quality hooks 顯示近期 preview_buy 穩定度偏弱' in payload['decision']['summary']


def test_agent_response_respects_quality_hook_raise_if_supported():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-qh-002",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00679B": {"rsi": 39}}},
                "decision_memory_context": {
                    "memory_notes": [],
                    "quality_hooks": {"confidence_bias": "raise_if_supported", "quality_summary": "recent preview_buy: reviewed=3, superseded=0"}
                }
            }
        }
        (state_dir / 'ai_decision_request.json').write_text(json.dumps(request_payload), encoding='utf-8')
        payload = module.generate_ai_agent_response_from_state_dir(state_dir, agent_name='ETF_Master')
        assert payload['decision']['confidence'] == 'medium'
