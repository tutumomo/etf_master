from pathlib import Path
import importlib.util
import tempfile
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_quality_state.py")
spec = importlib.util.spec_from_file_location("ai_decision_quality_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_quality_payload_contains_autoresearch_inspired_fields():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id": "x", "action": "preview_buy", "review_status": "reviewed"}, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )
        payload = module.build_ai_decision_quality_payload(state_dir)
        assert 'reviewed_rate' in payload
        assert 'superseded_rate' in payload
        assert 'confidence_calibration_hint' in payload
