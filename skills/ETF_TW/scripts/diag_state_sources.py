#!/usr/bin/env python3
from __future__ import annotations

"""P5-3: One-shot diagnosis for state source alignment (dashboard vs agent vs root).

Goal: prevent misreports caused by root-vs-instance drift or stale/derived snapshots.

Usage:
  python3 scripts/diag_state_sources.py
  python3 scripts/diag_state_sources.py --instance-id etf_master
  python3 scripts/diag_state_sources.py --state-dir <path>
  python3 scripts/diag_state_sources.py --strict

Output: JSON summary with paths, mtimes, embedded 'source' fields, and a verdict.
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def root_sensitive_present() -> list[str]:
    root_state = ROOT / "state"
    sensitive = [
        "positions.json",
        "account_snapshot.json",
        "orders_open.json",
        "portfolio_snapshot.json",
        "agent_summary.json",
        "strategy_link.json",
        "trading_mode.json",
        "watchlist.json",
        "intraday_tape_context.json",
    ]
    return [name for name in sensitive if (root_state / name).exists()]


def derive_state_dir(instance_id: str) -> Path:
    # canonical instance state
    return ROOT / "instances" / instance_id / "state"


def verdict(summary: dict, strict: bool = False) -> str:
    root_leaks = summary["root_state_guard"]["sensitive_present"]
    if root_leaks:
        if strict:
            raise SystemExit(2)
        return "ROOT_LEAK"

    # Must have instance positions + snapshot at least
    pos = summary["instance_state"]["positions"]
    snap = summary["instance_state"]["portfolio_snapshot"]
    if not pos["exists"] or not snap["exists"]:
        return "MISSING_CANONICAL"

    # Live-ready should never present paper_ledger as orders_open source.
    mode_src = summary["instance_state"]["trading_mode"].get("embedded_source")
    # The trading_mode file in state doesn't embed 'source' reliably; infer effective_mode from file content if present.
    # We store effective_mode optionally in the embedded_source-less payload via other scripts.
    # For safety: treat orders_open paper_ledger as drift when positions/snapshot are live_broker.
    orders_open_src = summary["instance_state"]["orders_open"].get("embedded_source")
    if orders_open_src == "paper_ledger" and pos.get("embedded_source") == "live_broker":
        return "DRIFT_ORDERS_OPEN_PAPER_IN_LIVE"

    return "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance-id", default="etf_master")
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    state_dir = Path(args.state_dir) if args.state_dir else derive_state_dir(args.instance_id)

    def file_summary(name: str) -> dict:
        p = state_dir / name
        j = load_json(p)
        return {
            "path": str(p),
            "exists": p.exists(),
            "mtime": mtime_iso(p),
            "embedded_source": j.get("source"),
        }

    out: dict[str, Any] = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "instance_id": args.instance_id,
        "instance_state_dir": str(state_dir),
        "root_state_guard": {
            "root_state_dir": str(ROOT / "state"),
            "sensitive_present": root_sensitive_present(),
        },
        "instance_state": {
            "positions": file_summary("positions.json"),
            "portfolio_snapshot": file_summary("portfolio_snapshot.json"),
            "agent_summary": file_summary("agent_summary.json"),
            "orders_open": file_summary("orders_open.json"),
            "strategy_link": file_summary("strategy_link.json"),
            "trading_mode": file_summary("trading_mode.json"),
        },
    }

    out["verdict"] = verdict(out, strict=args.strict)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
