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


def test_agent_response_prefers_ai_decision_quality_state_lower_bias():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d/'ai_decision_request.json').write_text(json.dumps({
            'request_id':'req-quality-001',
            'inputs': {
                'strategy': {'base_strategy':'核心累積','scenario_overlay':'逢低觀察'},
                'market_context_taiwan': {'risk_temperature':'normal'},
                'market_event_context': {'global_risk_level':'normal'},
                'market_intelligence': {'intelligence': {'00940': {'rsi': 40}}},
                'decision_memory_context': {'quality_hooks': {'confidence_bias': 'raise_if_supported'}}
            }
        }, ensure_ascii=False), encoding='utf-8')
        (d/'ai_decision_quality.json').write_text(json.dumps({
            'confidence_bias':'lower',
            'quality_summary':'state says lower'
        }, ensure_ascii=False), encoding='utf-8')
        payload = module.generate_ai_agent_response_from_state_dir(d, agent_name='ETF_Master')
        assert payload['decision']['confidence'] == 'low'
        assert 'quality hooks 顯示近期 preview_buy 穩定度偏弱' in payload['decision']['summary']


def test_agent_response_can_read_quality_state_raise_if_supported():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d/'ai_decision_request.json').write_text(json.dumps({
            'request_id':'req-quality-002',
            'inputs': {
                'strategy': {'base_strategy':'核心累積','scenario_overlay':'收益再投資'},
                'market_context_taiwan': {'risk_temperature':'normal'},
                'market_event_context': {'global_risk_level':'normal'},
                'market_intelligence': {'intelligence': {'00679B': {'rsi': 39}}},
                'decision_memory_context': {'quality_hooks': {'confidence_bias': 'neutral'}}
            }
        }, ensure_ascii=False), encoding='utf-8')
        (d/'ai_decision_quality.json').write_text(json.dumps({
            'confidence_bias':'raise_if_supported',
            'quality_summary':'state says raise'
        }, ensure_ascii=False), encoding='utf-8')
        payload = module.generate_ai_agent_response_from_state_dir(d, agent_name='ETF_Master')
        assert payload['decision']['confidence'] == 'medium'
