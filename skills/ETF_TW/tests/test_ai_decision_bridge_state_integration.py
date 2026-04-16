from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/ai_decision_bridge.py")
spec = importlib.util.spec_from_file_location("ai_decision_bridge", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_default_ai_decision_request_payload_has_expected_shape():
    payload = module.default_ai_decision_request_payload()
    assert payload["requested_by"] == "system"
    assert payload["mode"] == "decision_only"
    assert "request_id" in payload
    assert payload["inputs"] == {}


def test_default_ai_decision_response_payload_has_expected_shape():
    payload = module.default_ai_decision_response_payload()
    assert payload["source"] == "ai_decision_bridge"
    assert payload["decision"]["action"] == "hold"
    assert payload["stale"] is True
    assert payload["candidate"] == {}


def test_is_ai_decision_response_stale_respects_expires_at():
    fresh = module.build_ai_decision_response(
        request_id="req-fresh",
        summary="fresh",
        action="hold",
        confidence="medium",
        expires_in_minutes=30,
    )
    assert module.is_ai_decision_response_stale(fresh) is False

    stale = dict(fresh)
    stale["expires_at"] = "2000-01-01T00:00:00+08:00"
    assert module.is_ai_decision_response_stale(stale) is True
