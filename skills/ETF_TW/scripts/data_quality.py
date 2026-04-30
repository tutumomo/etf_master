#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.etf_core import context
    from scripts.state_reconciliation import reconciliation_summary
except ImportError:
    from etf_core import context
    from state_reconciliation import reconciliation_summary

STATE_DIR = context.get_state_dir()
OUTPUT_NAME = "data_quality_report.json"
FRESH_MINUTES = 60


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def canonicalize_symbol(symbol: str | None) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def market_cache_age_minutes(market_cache: dict, now: datetime | None = None) -> float | None:
    updated_at = parse_ts(market_cache.get("updated_at"))
    if not updated_at:
        return None
    now_value = now or datetime.now(tz=updated_at.tzinfo)
    if updated_at.tzinfo and now_value.tzinfo is None:
        now_value = now_value.replace(tzinfo=updated_at.tzinfo)
    if now_value.tzinfo and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=now_value.tzinfo)
    return (now_value - updated_at).total_seconds() / 60


def _symbols_from_rows(rows: list[dict], key: str = "symbol") -> set[str]:
    return {canonicalize_symbol(row.get(key)) for row in rows if canonicalize_symbol(row.get(key))}


def collect_required_symbols(watchlist: dict, positions: dict) -> set[str]:
    return _symbols_from_rows(watchlist.get("items", [])) | _symbols_from_rows(positions.get("positions", []))


def collect_missing_quotes(watchlist: dict, positions: dict, market_cache: dict) -> list[str]:
    quotes = market_cache.get("quotes") or {}
    quote_symbols = {canonicalize_symbol(symbol) for symbol in quotes.keys()}
    return sorted(collect_required_symbols(watchlist, positions) - quote_symbols)


def build_data_quality_report(state_dir: Path, now: datetime | None = None) -> dict[str, Any]:
    market_cache = load_json(state_dir / "market_cache.json", {"quotes": {}})
    watchlist = load_json(state_dir / "watchlist.json", {"items": []})
    positions = load_json(state_dir / "positions.json", {"positions": []})
    snapshot = load_json(state_dir / "portfolio_snapshot.json", {"holdings": []})
    orders_open = load_json(state_dir / "orders_open.json", {"orders": []})

    issues: list[str] = []
    warnings: list[str] = []

    age = market_cache_age_minutes(market_cache, now=now)
    quotes = market_cache.get("quotes") or {}
    if age is None:
        issues.append("market_cache_missing_or_unparseable_updated_at")
    elif age > FRESH_MINUTES:
        warnings.append("market_cache_stale_over_60_minutes")

    if not quotes:
        issues.append("market_cache_quotes_empty")

    missing_quotes = collect_missing_quotes(watchlist, positions, market_cache)
    if missing_quotes:
        issues.append("missing_required_quotes")

    reconciliation = reconciliation_summary(positions, snapshot, orders_open)
    if not reconciliation.get("positions_vs_snapshot_match", True):
        warnings.append("positions_snapshot_symbol_drift")
    if reconciliation.get("open_orders_not_in_positions"):
        warnings.append("open_orders_not_in_positions")

    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "missing_quote_symbols": missing_quotes,
        "freshness": {
            "market_cache_age_minutes": round(age, 2) if age is not None else None,
            "fresh_threshold_minutes": FRESH_MINUTES,
        },
        "reconciliation": reconciliation,
        "updated_at": (now or datetime.now()).isoformat(),
        "source": "data_quality",
    }


def refresh_data_quality_report(state_dir: Path = STATE_DIR, output_name: str = OUTPUT_NAME) -> dict:
    report = build_data_quality_report(state_dir)
    (state_dir / output_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check ETF_TW state data quality.")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="State directory to inspect")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    state_dir = Path(args.state_dir)
    report = refresh_data_quality_report(state_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("DATA_QUALITY_OK" if report["ok"] else "DATA_QUALITY_ISSUES")
        print(f"issues={len(report['issues'])} warnings={len(report['warnings'])}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
