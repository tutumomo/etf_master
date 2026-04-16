from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_quality_state.py")
spec = importlib.util.spec_from_file_location("ai_decision_quality_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_ai_decision_quality_payload_reads_quality_hooks_and_counts():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id": "a", "action": "preview_buy", "review_status": "superseded", "outcome_status": "reviewed", "reflection_note": "不夠穩定"}, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )
        payload = module.build_ai_decision_quality_payload(state_dir)
        assert payload['confidence_bias'] == 'neutral' or payload['confidence_bias'] == 'lower'
        assert 'quality_summary' in payload
        assert 'updated_at' in payload


def test_write_ai_decision_quality_state_writes_file():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        payload = module.write_ai_decision_quality_state(state_dir)
        written = json.loads((state_dir / 'ai_decision_quality.json').read_text(encoding='utf-8'))
        assert written['updated_at'] == payload['updated_at']
