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


def test_auto_post_review_cycle_uses_market_cache_to_write_price_delta_note():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_response.json').write_text(json.dumps({
            'request_id': 'req-market-001',
            'source': 'ai_agent',
            'candidate': {'symbol': '00940', 'reference_price': 10.0},
            'decision': {'action': 'preview_buy', 'summary': 'AI agent 建議優先觀察 00940'},
            'review': {'status': 'reviewed', 'human_feedback': '可接受'}
        }, ensure_ascii=False), encoding='utf-8')
        (state_dir / 'market_cache.json').write_text(json.dumps({
            'quotes': {'00940': {'current_price': 10.8}}
        }, ensure_ascii=False), encoding='utf-8')
        result = module.run_auto_post_review_cycle(state_dir, outcome_note='隔日自動復盤')
        assert result['outcome']['outcome_status'] == 'reviewed'
        assert '較建議參考價上升' in result['outcome']['outcome_note']
