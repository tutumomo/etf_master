#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context
from filled_reconciliation import build_reconciliation_report, save_reconciliation_report


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_reconciliation_report(state_dir: Path) -> dict:
    fills_payload = load_json(state_dir / "fills_ledger.json")
    positions_payload = load_json(state_dir / "positions.json")
    report = build_reconciliation_report(fills_payload, positions_payload)
    save_reconciliation_report(state_dir / "filled_reconciliation.json", report)
    return report


def main() -> int:
    state_dir = context.get_state_dir()
    report = refresh_reconciliation_report(state_dir)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
