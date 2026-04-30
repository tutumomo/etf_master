#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context
from order_event_bridge import event_payload_to_order_row
from orders_open_state import build_orders_open_payload, merge_open_orders
from fills_ledger import load_fills_ledger as _load_fills_ledger, save_fills_ledger as _save_fills_ledger, merge_fill_facts

ORDERS_OPEN_PATH = context.get_state_dir() / "orders_open.json"
FILLS_LEDGER_PATH = context.get_state_dir() / "fills_ledger.json"


def load_orders_open() -> dict:
    if not ORDERS_OPEN_PATH.exists():
        return {"orders": [], "source": "live_broker"}
    return json.loads(ORDERS_OPEN_PATH.read_text(encoding="utf-8"))


def save_orders_open(rows: list[dict]) -> None:
    payload = build_orders_open_payload(rows, source="live_broker")
    ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_fills_ledger() -> dict:
    return _load_fills_ledger(FILLS_LEDGER_PATH)


def save_fills_ledger(rows: list[dict]) -> None:
    _save_fills_ledger(FILLS_LEDGER_PATH, rows)


def handle_order_event(event_type: str, payload: dict) -> bool:
    row = event_payload_to_order_row(event_type, payload)
    if not row:
        return False

    current_rows = load_orders_open().get("orders", [])
    save_orders_open(merge_open_orders(current_rows, row))

    if row.get("status") in {"partial_filled", "filled"}:
        current_fills = load_fills_ledger().get("fills", [])
        save_fills_ledger(merge_fill_facts(current_fills, row))

    return True
