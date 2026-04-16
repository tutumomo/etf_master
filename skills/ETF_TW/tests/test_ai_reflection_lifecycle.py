from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_reflection_lifecycle.py")
spec = importlib.util.spec_from_file_location("ai_reflection_lifecycle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_record_reflection_writes_reflection_ledger():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-reflect-001",
            "source": "ai_agent",
            "candidate": {"symbol": "00940"},
            "decision": {"action": "preview_buy", "summary": "AI agent 建議優先觀察 00940"},
            "review": {"status": "reviewed", "human_feedback": "合理"}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        (state_dir / "ai_decision_outcome.jsonl").write_text(json.dumps({"request_id": "req-reflect-001", "outcome_status": "reviewed", "outcome_note": "後續合理"}, ensure_ascii=False) + "\n", encoding="utf-8")
        row = module.record_reflection(state_dir, reflection_note="此建議可保留作為下次基準")
        assert row["request_id"] == "req-reflect-001"
        assert row["symbol"] == "00940"
        assert row["reflection_note"] == "此建議可保留作為下次基準"
        assert row["review_status"] == "reviewed"
        assert row["outcome_status"] == "reviewed"

        ledger = (state_dir / "ai_decision_reflection.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(ledger) == 1


def test_record_reflection_handles_missing_outcome_gracefully():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-reflect-002",
            "source": "ai_agent",
            "candidate": {"symbol": "0050"},
            "decision": {"action": "watch_only", "summary": "先觀察"},
            "review": {"status": "pending", "human_feedback": None}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        row = module.record_reflection(state_dir, reflection_note="暫無 outcome，先留痕")
        assert row["outcome_status"] == "unknown"
