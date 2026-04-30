from datetime import datetime
from pathlib import Path
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import data_quality as module


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_data_quality_report_ok_when_quotes_fresh_and_symbols_match(tmp_path: Path):
    _write(tmp_path / "market_cache.json", {
        "updated_at": "2026-04-30T10:00:00",
        "quotes": {"006208": {"current_price": 211.5}},
    })
    _write(tmp_path / "watchlist.json", {"items": [{"symbol": "006208.TW"}]})
    _write(tmp_path / "positions.json", {
        "positions": [{"symbol": "006208"}],
        "updated_at": "2026-04-30T10:00:00",
    })
    _write(tmp_path / "portfolio_snapshot.json", {
        "holdings": [{"symbol": "006208"}],
        "updated_at": "2026-04-30T10:00:10",
    })
    _write(tmp_path / "orders_open.json", {"orders": []})

    report = module.build_data_quality_report(tmp_path, now=datetime.fromisoformat("2026-04-30T10:30:00"))

    assert report["ok"] is True
    assert report["issues"] == []
    assert report["missing_quote_symbols"] == []


def test_build_data_quality_report_flags_missing_required_quotes(tmp_path: Path):
    _write(tmp_path / "market_cache.json", {
        "updated_at": "2026-04-30T10:00:00",
        "quotes": {"0050": {"current_price": 180}},
    })
    _write(tmp_path / "watchlist.json", {"items": [{"symbol": "006208"}]})
    _write(tmp_path / "positions.json", {"positions": [{"symbol": "00878"}]})
    _write(tmp_path / "portfolio_snapshot.json", {"holdings": [{"symbol": "00878"}]})
    _write(tmp_path / "orders_open.json", {"orders": []})

    report = module.build_data_quality_report(tmp_path, now=datetime.fromisoformat("2026-04-30T10:30:00"))

    assert report["ok"] is False
    assert "missing_required_quotes" in report["issues"]
    assert report["missing_quote_symbols"] == ["006208", "00878"]


def test_build_data_quality_report_warns_on_stale_cache_and_symbol_drift(tmp_path: Path):
    _write(tmp_path / "market_cache.json", {
        "updated_at": "2026-04-30T08:00:00",
        "quotes": {"006208": {"current_price": 211.5}},
    })
    _write(tmp_path / "watchlist.json", {"items": [{"symbol": "006208"}]})
    _write(tmp_path / "positions.json", {
        "positions": [{"symbol": "006208"}],
        "updated_at": "2026-04-30T08:00:00",
    })
    _write(tmp_path / "portfolio_snapshot.json", {
        "holdings": [{"symbol": "0050"}],
        "updated_at": "2026-04-30T08:00:10",
    })
    _write(tmp_path / "orders_open.json", {"orders": [{"symbol": "00922"}]})

    report = module.build_data_quality_report(tmp_path, now=datetime.fromisoformat("2026-04-30T10:30:00"))

    assert report["ok"] is True
    assert "market_cache_stale_over_60_minutes" in report["warnings"]
    assert "positions_snapshot_symbol_drift" in report["warnings"]
    assert "open_orders_not_in_positions" in report["warnings"]
