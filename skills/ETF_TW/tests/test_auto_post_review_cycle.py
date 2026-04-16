from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/auto_post_review_cycle.py")
spec = importlib.util.spec_from_file_location("auto_post_review_cycle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_auto_post_review_cycle_records_outcome_and_reflection_for_existing_response():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({
            'request_id': 'req-cycle-001',
            'source': 'ai_agent',
            'candidate': {'symbol': '00940'},
            'decision': {'action': 'preview_buy', 'summary': 'AI agent 建議優先觀察 00940'},
            'review': {'status': 'reviewed', 'human_feedback': '可接受'}
        }, ensure_ascii=False), encoding='utf-8')
        result = module.run_auto_post_review_cycle(state_dir, outcome_note='隔日自動復盤')
        assert result['outcome']['request_id'] == 'req-cycle-001'
        assert result['reflection']['request_id'] == 'req-cycle-001'
        assert result['outcome']['outcome_status'] == 'tracked'

        outcome_lines = (state_dir / 'ai_decision_outcome.jsonl').read_text(encoding='utf-8').strip().splitlines()
        reflection_lines = (state_dir / 'ai_decision_reflection.jsonl').read_text(encoding='utf-8').strip().splitlines()
        assert len(outcome_lines) == 1
        assert len(reflection_lines) == 1


def test_auto_post_review_cycle_skips_when_no_request_id():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({'source': 'ai_agent'}, ensure_ascii=False), encoding='utf-8')
        result = module.run_auto_post_review_cycle(state_dir, outcome_note='隔日自動復盤')
        assert result['skipped'] is True
