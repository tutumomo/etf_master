from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/generate_ai_decision_request.py")
spec = importlib.util.spec_from_file_location("generate_ai_decision_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_request_payload_from_state_dir_writes_request_file():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / "strategy_link.json").write_text(json.dumps({"base_strategy": "核心累積", "scenario_overlay": "收益再投資"}), encoding="utf-8")
        (state_dir / "positions.json").write_text(json.dumps({"positions": [{"symbol": "0050", "quantity": 100}]}), encoding="utf-8")
        (state_dir / "orders_open.json").write_text(json.dumps({"orders": []}), encoding="utf-8")
        (state_dir / "fills_ledger.json").write_text(json.dumps({"fills": []}), encoding="utf-8")
        (state_dir / "portfolio_snapshot.json").write_text(json.dumps({"holdings": []}), encoding="utf-8")
        (state_dir / "market_cache.json").write_text(json.dumps({"quotes": {}}), encoding="utf-8")
        (state_dir / "market_intelligence.json").write_text(json.dumps({"intelligence": {}}), encoding="utf-8")
        (state_dir / "intraday_tape_context.json").write_text(json.dumps({"watchlist_signals": []}), encoding="utf-8")
        (state_dir / "market_context_taiwan.json").write_text(json.dumps({"risk_temperature": "normal"}), encoding="utf-8")
        (state_dir / "market_event_context.json").write_text(json.dumps({"global_risk_level": "normal"}), encoding="utf-8")
        (state_dir / "market_calendar_tw.json").write_text(json.dumps({"date": "2026-04-03", "is_open": True, "session": "trading_day"}), encoding="utf-8")
        (state_dir / "filled_reconciliation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

        payload = module.generate_request_payload_from_state_dir(state_dir, requested_by="dashboard", mode="preview_only")
        assert payload["requested_by"] == "dashboard"
        assert payload["mode"] == "preview_only"
        assert payload["inputs"]["positions"]["positions"][0]["symbol"] == "0050"

        written = json.loads((state_dir / "ai_decision_request.json").read_text(encoding="utf-8"))
        assert written["request_id"] == payload["request_id"]
        assert written["inputs"]["market_calendar_status"]["session"] == "trading_day"


# ---------------------------------------------------------------------------
# C1: _read_learned_rules_freshness
# ---------------------------------------------------------------------------

def test_learned_rules_freshness_empty_meta():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        # No learned_rules_meta.json present
        result = module._read_learned_rules_freshness(state_dir, [])
        assert result["total_rules"] == 0
        assert result["knowledge_healthy"] == False
        assert result["most_recent_update"] is None


def test_learned_rules_freshness_healthy():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        meta = {
            "rules": [
                {"rule_id": "RULE-001", "rule_text": "Rule one", "source_stats": "", "count": 3, "first_seen": "2026-W10", "last_confirmed": "2026-W14", "status": "active"},
                {"rule_id": "RULE-002", "rule_text": "Rule two", "source_stats": "", "count": 2, "first_seen": "2026-W12", "last_confirmed": "2026-W15", "status": "active"},
                {"rule_id": "RULE-003", "rule_text": "Rule three", "source_stats": "", "count": 1, "first_seen": "2026-W15", "last_confirmed": "2026-W15", "status": "tentative"},
            ]
        }
        (state_dir / "learned_rules_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        result = module._read_learned_rules_freshness(state_dir, [])
        assert result["total_rules"] == 3
        assert result["active"] == 2
        assert result["tentative"] == 1
        assert result["stale"] == 0
        assert result["knowledge_healthy"] == True
        assert result["most_recent_update"] == "2026-W15"


def test_learned_rules_freshness_all_stale():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        meta = {
            "rules": [
                {"rule_id": "RULE-001", "rule_text": "Rule one", "source_stats": "", "count": 2, "first_seen": "2026-W01", "last_confirmed": "2026-W02", "status": "stale"},
                {"rule_id": "RULE-002", "rule_text": "Rule two", "source_stats": "", "count": 1, "first_seen": "2026-W03", "last_confirmed": "2026-W04", "status": "stale"},
            ]
        }
        (state_dir / "learned_rules_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        result = module._read_learned_rules_freshness(state_dir, [])
        assert result["knowledge_healthy"] == False


# ---------------------------------------------------------------------------
# C2: _compute_input_fingerprint
# ---------------------------------------------------------------------------

def _make_fingerprint_payload(market_regime: str) -> dict:
    """Build a minimal payload with the nested structure _compute_input_fingerprint expects."""
    return {
        "inputs": {
            "market_context_taiwan": {"market_regime": market_regime, "risk_temperature": "elevated"},
            "market_event_context": {"global_risk_level": "normal", "defensive_bias": False},
            "intraday_tape_context": {"market_bias": "neutral"},
            "strategy": {"base_strategy": "核心累積", "scenario_overlay": "收益再投資"},
            "positions": {"positions": [{"symbol": "0050"}]},
        }
    }


def test_compute_input_fingerprint_stable():
    payload = _make_fingerprint_payload("cautious")
    result1 = module._compute_input_fingerprint(payload)
    result2 = module._compute_input_fingerprint(payload)
    assert result1 == result2
    assert len(result1) == 12


def test_compute_input_fingerprint_changes_with_input():
    payload_a = _make_fingerprint_payload("cautious")
    payload_b = _make_fingerprint_payload("neutral")
    fp_a = module._compute_input_fingerprint(payload_a)
    fp_b = module._compute_input_fingerprint(payload_b)
    assert fp_a != fp_b


def test_request_payload_includes_input_fingerprint():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / "strategy_link.json").write_text(json.dumps({"base_strategy": "核心累積", "scenario_overlay": "收益再投資"}), encoding="utf-8")
        (state_dir / "positions.json").write_text(json.dumps({"positions": [{"symbol": "0050", "quantity": 100}]}), encoding="utf-8")
        (state_dir / "orders_open.json").write_text(json.dumps({"orders": []}), encoding="utf-8")
        (state_dir / "fills_ledger.json").write_text(json.dumps({"fills": []}), encoding="utf-8")
        (state_dir / "portfolio_snapshot.json").write_text(json.dumps({"holdings": []}), encoding="utf-8")
        (state_dir / "market_cache.json").write_text(json.dumps({"quotes": {}}), encoding="utf-8")
        (state_dir / "market_intelligence.json").write_text(json.dumps({"intelligence": {}}), encoding="utf-8")
        (state_dir / "intraday_tape_context.json").write_text(json.dumps({"watchlist_signals": []}), encoding="utf-8")
        (state_dir / "market_context_taiwan.json").write_text(json.dumps({"risk_temperature": "normal"}), encoding="utf-8")
        (state_dir / "market_event_context.json").write_text(json.dumps({"global_risk_level": "normal"}), encoding="utf-8")
        (state_dir / "market_calendar_tw.json").write_text(json.dumps({"date": "2026-04-03", "is_open": True, "session": "trading_day"}), encoding="utf-8")
        (state_dir / "filled_reconciliation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

        payload = module.generate_request_payload_from_state_dir(state_dir)
        assert "input_fingerprint" in payload
        assert len(payload["input_fingerprint"]) == 12

        written = json.loads((state_dir / "ai_decision_request.json").read_text(encoding="utf-8"))
        assert payload["input_fingerprint"] in json.dumps(written)
