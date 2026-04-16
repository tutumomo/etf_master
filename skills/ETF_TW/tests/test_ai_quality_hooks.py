from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_quality_hooks.py")
spec = importlib.util.spec_from_file_location("ai_quality_hooks", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_quality_hooks_detects_superseded_bias():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id": "a", "symbol": "00940", "action": "preview_buy", "review_status": "superseded", "outcome_status": "reviewed", "reflection_note": "最近常被新版取代"}, ensure_ascii=False) + '\n' +
            json.dumps({"request_id": "b", "symbol": "00940", "action": "preview_buy", "review_status": "superseded", "outcome_status": "reviewed", "reflection_note": "不夠穩定"}, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )
        hooks = module.build_quality_hooks(state_dir, limit=10)
        assert hooks['superseded_preview_buy_count'] == 2
        assert hooks['confidence_bias'] == 'lower'
        assert 'preview_buy' in hooks['quality_summary']


def test_build_quality_hooks_detects_reviewed_bias():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id": "c", "symbol": "00679B", "action": "preview_buy", "review_status": "reviewed", "outcome_status": "reviewed", "reflection_note": "可保留"}, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )
        hooks = module.build_quality_hooks(state_dir, limit=10)
        assert hooks['reviewed_preview_buy_count'] == 1
        assert hooks['confidence_bias'] in {'neutral', 'raise_if_supported'}
