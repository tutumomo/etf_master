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
