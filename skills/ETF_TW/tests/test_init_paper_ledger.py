from pathlib import Path
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import init_paper_ledger as module


def test_parse_position_normalizes_symbol_and_timestamp():
    parsed = module.parse_position("006208,8,211.5,2026-04-29")
    assert parsed == {
        "symbol": "006208",
        "quantity": 8,
        "price": 211.5,
        "timestamp": "2026-04-29T00:00:00",
    }


def test_build_initial_ledger_uses_trades_contract():
    ledger = module.build_initial_ledger([
        {"symbol": "006208", "quantity": 8, "price": 211.5, "timestamp": "2026-04-29T00:00:00"}
    ], created_at="2026-04-30T10:00:00")
    assert ledger["version"] == "1.0"
    assert ledger["source"] == "manual_initialization"
    assert ledger["trades"] == [{
        "symbol": "006208",
        "side": "buy",
        "quantity": 8,
        "price": 211.5,
        "estimated_total_cost": 1692.0,
        "timestamp": "2026-04-29T00:00:00",
        "source": "initial_position",
    }]


def test_write_initial_ledger_refuses_existing_trades_without_force(tmp_path: Path):
    path = tmp_path / "paper_ledger.json"
    path.write_text(json.dumps({"version": "1.0", "trades": [{"symbol": "0050"}]}), encoding="utf-8")
    try:
        module.write_initial_ledger(path, {"version": "1.0", "trades": []})
    except FileExistsError as exc:
        assert "already contains trades" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")


def test_write_initial_ledger_allows_empty_existing_ledger(tmp_path: Path):
    path = tmp_path / "paper_ledger.json"
    path.write_text(json.dumps({"version": "1.0", "trades": []}), encoding="utf-8")
    module.write_initial_ledger(path, {"version": "1.0", "trades": [{"symbol": "0050"}]})
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["trades"] == [{"symbol": "0050"}]
