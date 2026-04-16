from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_review_lifecycle.py")
spec = importlib.util.spec_from_file_location("ai_review_lifecycle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_update_review_status_writes_response_and_ledger():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-review-001",
            "source": "ai_agent",
            "review": {"status": "pending", "reviewed_at": None, "human_feedback": None}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        updated = module.update_review_status(state_dir, status="reviewed", human_feedback="這次建議合理")
        assert updated["review"]["status"] == "reviewed"
        assert updated["review"]["human_feedback"] == "這次建議合理"
        assert updated["review"]["reviewed_at"] is not None

        ledger = (state_dir / "ai_decision_review.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(ledger) == 1
        row = json.loads(ledger[0])
        assert row["request_id"] == "req-review-001"
        assert row["status"] == "reviewed"


def test_update_review_status_can_mark_superseded():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-review-002",
            "source": "ai_agent",
            "review": {"status": "pending", "reviewed_at": None, "human_feedback": None}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        updated = module.update_review_status(state_dir, status="superseded", human_feedback="新版建議已取代")
        assert updated["review"]["status"] == "superseded"
