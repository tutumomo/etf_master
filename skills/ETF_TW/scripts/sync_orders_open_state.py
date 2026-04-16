#!/usr/bin/env python3
from __future__ import annotations

"""Ensure orders_open.json is aligned with the current effective trading mode.

Problem:
- In live-ready mode, orders_open.json could remain from legacy paper sync (source=paper_ledger),
  causing dashboard/agent drift and misleading reconciliation.

Current approach (safe + minimal):
- If effective_mode == live-ready:
  - Treat orders_open.json as *live* view of non-terminal orders.
  - If the current file is missing, or its source is paper_ledger, reset it to an empty live_broker payload.
  - If the current file is live_broker (or other non-paper source), keep existing orders but normalize shape.

Note:
- This script does NOT query broker open orders (adapter interface currently lacks list-open-orders).
  It only prevents incorrect paper-ledger residue from being presented in live-ready mode.
"""

import json
from datetime import datetime
from pathlib import Path
import sys

from trading_mode import read_trading_mode_state

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

from orders_open_state import build_orders_open_payload

STATE_DIR = context.get_state_dir()
ORDERS_OPEN_PATH = STATE_DIR / "orders_open.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    mode_state = read_trading_mode_state()
    if mode_state.get("effective_mode") != "live-ready":
        print("ORDERS_OPEN_SYNC_SKIPPED_NOT_LIVE_READY")
        return 0

    current = load_json(ORDERS_OPEN_PATH)
    source = current.get("source")

    # If legacy paper residue, reset to an empty live payload.
    if not ORDERS_OPEN_PATH.exists() or source == "paper_ledger":
        payload = build_orders_open_payload([], source="live_broker")
        payload["reset_reason"] = "paper_ledger_residue_in_live_ready"
        payload["effective_mode"] = "live-ready"
        ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ORDERS_OPEN_RESET_OK")
        return 0

    # Otherwise, keep orders but ensure minimal required keys.
    orders = current.get("orders") if isinstance(current.get("orders"), list) else []
    payload = build_orders_open_payload(orders, source=source or "live_broker")
    payload["effective_mode"] = "live-ready"
    ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ORDERS_OPEN_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
