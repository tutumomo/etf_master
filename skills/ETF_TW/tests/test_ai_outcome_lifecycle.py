from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_outcome_lifecycle.py")
spec = importlib.util.spec_from_file_location("ai_outcome_lifecycle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_record_outcome_writes_outcome_ledger():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-outcome-001",
            "source": "ai_agent",
            "candidate": {"symbol": "00940"},
            "decision": {"action": "preview_buy", "summary": "AI agent 建議優先觀察 00940"}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        row = module.record_outcome(state_dir, outcome_status="tracked", outcome_note="後續追蹤中")
        assert row["request_id"] == "req-outcome-001"
        assert row["symbol"] == "00940"
        assert row["outcome_status"] == "tracked"

        ledger = (state_dir / "ai_decision_outcome.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(ledger) == 1


def test_record_outcome_can_store_manual_feedback():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        response_payload = {
            "request_id": "req-outcome-002",
            "source": "ai_agent",
            "candidate": {"symbol": "0050"},
            "decision": {"action": "watch_only", "summary": "先觀察"}
        }
        (state_dir / "ai_decision_response.json").write_text(json.dumps(response_payload), encoding="utf-8")
        row = module.record_outcome(state_dir, outcome_status="reviewed", outcome_note="人工確認此建議合理", human_feedback="保留此方向")
        assert row["human_feedback"] == "保留此方向"
        assert row["outcome_note"] == "人工確認此建議合理"
