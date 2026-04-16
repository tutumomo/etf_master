from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_bridge.py")
spec = importlib.util.spec_from_file_location("ai_decision_bridge", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_ai_decision_request_minimum_contract():
    payload = module.build_ai_decision_request(
        requested_by="dashboard",
        mode="preview_only",
        context_version="ctx-001",
        inputs={"positions": {"items": []}, "market_intelligence": {"intelligence": {}}},
    )
    assert payload["requested_by"] == "dashboard"
    assert payload["mode"] == "preview_only"
    assert payload["context_version"] == "ctx-001"
    assert "request_id" in payload
    assert "created_at" in payload
    assert "context_updated_at" in payload
    assert payload["inputs"]["positions"] == {"items": []}


def test_build_ai_decision_response_minimum_contract():
    payload = module.build_ai_decision_response(
        request_id="req-001",
        summary="建議先觀望",
        action="hold",
        confidence="medium",
    )
    assert payload["request_id"] == "req-001"
    assert payload["decision"]["summary"] == "建議先觀望"
    assert payload["decision"]["action"] == "hold"
    assert payload["decision"]["confidence"] == "medium"
    assert payload["source"] == "ai_decision_bridge"
    assert "generated_at" in payload
    assert "expires_at" in payload
    assert payload["stale"] is False


def test_build_ai_decision_response_includes_candidate_and_warnings():
    payload = module.build_ai_decision_response(
        request_id="req-002",
        summary="建議建立 00679B preview",
        action="preview_buy",
        confidence="high",
        candidate={"symbol": "00679B", "side": "buy"},
        warnings=["market_intelligence stale"],
    )
    assert payload["candidate"]["symbol"] == "00679B"
    assert payload["warnings"] == ["market_intelligence stale"]
