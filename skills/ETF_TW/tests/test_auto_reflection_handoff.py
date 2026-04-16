from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_auto_reflection.py")
spec = importlib.util.spec_from_file_location("ai_auto_reflection", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_auto_reflection_after_review_and_outcome_creates_reflection_entry():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({
            'request_id': 'req-auto-001',
            'source': 'ai_agent',
            'candidate': {'symbol': '00940'},
            'decision': {'action': 'preview_buy', 'summary': 'AI agent 建議優先觀察 00940'},
            'review': {'status': 'reviewed', 'human_feedback': '這次建議合理'}
        }, ensure_ascii=False), encoding='utf-8')
        (state_dir / 'ai_decision_outcome.jsonl').write_text(json.dumps({
            'request_id': 'req-auto-001',
            'outcome_status': 'tracked',
            'outcome_note': '後續追蹤中'
        }, ensure_ascii=False) + '\n', encoding='utf-8')
        row = module.auto_reflect_if_ready(state_dir)
        assert row is not None
        assert row['request_id'] == 'req-auto-001'
        assert row['review_status'] == 'reviewed'
        assert row['outcome_status'] == 'tracked'


def test_auto_reflection_skips_when_review_still_pending():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({
            'request_id': 'req-auto-002',
            'source': 'ai_agent',
            'candidate': {'symbol': '0050'},
            'decision': {'action': 'watch_only', 'summary': '先觀察'},
            'review': {'status': 'pending', 'human_feedback': None}
        }, ensure_ascii=False), encoding='utf-8')
        row = module.auto_reflect_if_ready(state_dir)
        assert row is None
