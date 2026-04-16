from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_bridge.py")
spec = importlib.util.spec_from_file_location("ai_decision_bridge", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_agent_consumed_response_payload_marks_agent_source_and_review_fields():
    payload = module.build_agent_consumed_response_payload(
        request_id="req-agent-001",
        summary="建議先觀察 0050，等待更明確訊號。",
        action="watch_only",
        confidence="medium",
        agent_name="ETF_Master",
        review_status="pending",
    )
    assert payload["source"] == "ai_agent"
    assert payload["agent"]["name"] == "ETF_Master"
    assert payload["review"]["status"] == "pending"
    assert "generated_at" in payload
    assert payload["decision"]["action"] == "watch_only"


def test_build_agent_consumed_response_payload_keeps_reasoning_and_input_refs():
    payload = module.build_agent_consumed_response_payload(
        request_id="req-agent-002",
        summary="建議建立 00679B preview。",
        action="preview_buy",
        confidence="high",
        agent_name="ETF_Master",
        review_status="pending",
        reasoning={"market_context_summary": "risk-off", "risk_context_summary": "需保守"},
        input_refs={"request": "ai_decision_request.json"},
    )
    assert payload["reasoning"]["market_context_summary"] == "risk-off"
    assert payload["input_refs"]["request"] == "ai_decision_request.json"
