from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_memory_context.py")
spec = importlib.util.spec_from_file_location("ai_decision_memory_context", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_decision_memory_context_reads_recent_review_outcome_reflection():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / 'ai_decision_review.jsonl').write_text(
            json.dumps({"request_id": "req-1", "status": "reviewed", "human_feedback": "合理"}, ensure_ascii=False) + "\n",
            encoding='utf-8'
        )
        (state_dir / 'ai_decision_outcome.jsonl').write_text(
            json.dumps({"request_id": "req-1", "outcome_status": "reviewed", "outcome_note": "後續合理"}, ensure_ascii=False) + "\n",
            encoding='utf-8'
        )
        (state_dir / 'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id": "req-1", "symbol": "00940", "reflection_note": "保留作為下次基準"}, ensure_ascii=False) + "\n",
            encoding='utf-8'
        )
        ctx = module.build_decision_memory_context(state_dir, limit=5)
        assert ctx['recent_review_count'] == 1
        assert ctx['recent_outcome_count'] == 1
        assert ctx['recent_reflection_count'] == 1
        assert ctx['memory_notes'][0]['request_id'] == 'req-1'
        assert ctx['memory_notes'][0]['reflection_note'] == '保留作為下次基準'


def test_build_decision_memory_context_defaults_when_ledgers_missing():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        ctx = module.build_decision_memory_context(state_dir, limit=3)
        assert ctx['recent_review_count'] == 0
        assert ctx['recent_outcome_count'] == 0
        assert ctx['recent_reflection_count'] == 0
        assert ctx['memory_notes'] == []
