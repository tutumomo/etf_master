from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_decision_response.py")
spec = importlib.util.spec_from_file_location("generate_ai_decision_response", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_response_payload_from_request_writes_response_file():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-001",
            "requested_by": "dashboard",
            "mode": "preview_only",
            "context_version": "核心累積::收益再投資",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
                "positions": {"positions": []},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"00679B": {"rsi": 48}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")

        payload = module.generate_response_payload_from_state_dir(state_dir)
        assert payload["request_id"] == "req-001"
        assert payload["source"] == "ai_decision_bridge"
        assert payload["decision"]["action"] in {"hold", "preview_buy", "watch_only"}

        written = json.loads((state_dir / "ai_decision_response.json").read_text(encoding="utf-8"))
        assert written["request_id"] == "req-001"
        assert "summary" in written["decision"]


def test_generate_response_payload_marks_preview_candidate_when_intelligence_exists():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        request_payload = {
            "request_id": "req-002",
            "requested_by": "system",
            "mode": "decision_only",
            "context_version": "核心累積::逢低觀察",
            "inputs": {
                "strategy": {"base_strategy": "核心累積", "scenario_overlay": "逢低觀察"},
                "positions": {"positions": []},
                "market_context_taiwan": {"risk_temperature": "normal"},
                "market_event_context": {"global_risk_level": "normal"},
                "market_intelligence": {"intelligence": {"0050": {"rsi": 52}, "00679B": {"rsi": 44}}}
            }
        }
        (state_dir / "ai_decision_request.json").write_text(json.dumps(request_payload), encoding="utf-8")
        payload = module.generate_response_payload_from_state_dir(state_dir)
        assert payload["candidate"]["symbol"] in {"0050", "00679B"}
        assert payload["decision"]["confidence"] in {"medium", "high"}
