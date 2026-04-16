#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


def collect_unreconciled_filled_symbols(fills_payload: dict, positions_payload: dict) -> list[str]:
    fill_symbols = []
    for row in fills_payload.get("fills", []):
        if row.get("status") == "filled":
            symbol = row.get("symbol")
            if symbol and symbol not in fill_symbols:
                fill_symbols.append(symbol)

    position_symbols = {row.get("symbol") for row in positions_payload.get("positions", []) if row.get("symbol")}
    return [symbol for symbol in fill_symbols if symbol not in position_symbols]


def build_reconciliation_report(fills_payload: dict, positions_payload: dict) -> dict:
    unreconciled = collect_unreconciled_filled_symbols(fills_payload, positions_payload)
    return {
        "ok": len(unreconciled) == 0,
        "unreconciled_symbols": unreconciled,
        "unreconciled_count": len(unreconciled),
        "source": "filled_reconciliation",
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def load_reconciliation_report(path: Path) -> dict:
    if not path.exists():
        return {
            "ok": True,
            "unreconciled_symbols": [],
            "unreconciled_count": 0,
            "source": "filled_reconciliation",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_reconciliation_report(path: Path, report: dict) -> None:
    payload = dict(report)
    payload.setdefault("updated_at", datetime.now().astimezone().isoformat())
    payload.setdefault("source", "filled_reconciliation")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_reconciliation_warnings(report: dict) -> list[str]:
    if report.get("ok", True):
        return []
    warnings = []
    for symbol in report.get("unreconciled_symbols", []):
        warnings.append(f"filled_reconciliation: {symbol} 尚未對齊 positions")
    return warnings
