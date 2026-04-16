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


def test_auto_post_review_cycle_persists_review_window_metadata():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({
            'request_id': 'req-layer-001',
            'source': 'ai_agent',
            'candidate': {'symbol': '00940', 'reference_price': 10.0},
            'decision': {'action': 'preview_buy', 'summary': 'AI agent 建議優先觀察 00940'},
            'review': {'status': 'reviewed', 'human_feedback': '可接受'}
        }, ensure_ascii=False), encoding='utf-8')
        (state_dir / 'market_cache.json').write_text(json.dumps({'quotes': {'00940': {'current_price': 10.5}}}, ensure_ascii=False), encoding='utf-8')
        result = module.run_auto_post_review_cycle(state_dir, review_window='short_review', outcome_note='短期自動復盤')
        assert result['review_window']['name'] == 'short_review'
        assert result['outcome']['review_window'] == 'short_review'
        assert result['outcome']['review_window_label'] == 'T+3 短期復盤'
