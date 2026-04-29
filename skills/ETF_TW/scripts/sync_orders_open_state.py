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

In live-ready mode this also consumes broker deal records when available, so filled
orders do not remain in the local open-order view.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

from trading_mode import read_trading_mode_state

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

from orders_open_state import build_orders_open_payload, merge_open_orders

STATE_DIR = context.get_state_dir()
ORDERS_OPEN_PATH = STATE_DIR / "orders_open.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _record_payload(record) -> dict:
    payload = getattr(record, "record", record)
    return payload if isinstance(payload, dict) else {}


def _deal_rows_from_records(open_orders: list[dict], records) -> list[dict]:
    """Build terminal filled rows from broker deal records for currently open ordnos."""
    by_ordno = {
        str(row.get("broker_order_id") or ""): row
        for row in open_orders
        if row.get("broker_order_id")
    }
    rows: list[dict] = []
    seen: set[str] = set()

    for item in records or []:
        payload = _record_payload(item)
        deal = payload
        order = payload.get("order") if isinstance(payload.get("order"), dict) else {}

        ordno = str(deal.get("ordno") or order.get("ordno") or "")
        if not ordno or ordno not in by_ordno or ordno in seen:
            continue

        existing = by_ordno[ordno]
        symbol = deal.get("code") or payload.get("code") or order.get("code") or existing.get("symbol")
        action = str(deal.get("action") or order.get("action") or existing.get("action") or "").lower()
        quantity = deal.get("quantity") or order.get("quantity") or existing.get("quantity")
        price = deal.get("price") or order.get("price") or existing.get("price")

        rows.append({
            **existing,
            "order_id": existing.get("order_id"),
            "broker_order_id": ordno,
            "symbol": symbol,
            "action": action,
            "quantity": int(quantity or 0),
            "price": price,
            "filled_quantity": int(quantity or 0),
            "filled_price": price,
            "status": "filled",
            "broker_status": "filled",
            "source": "live_broker",
            "source_type": "broker_deal_records",
            "verified": True,
            "observed_at": datetime.now().astimezone().isoformat(),
        })
        seen.add(ordno)

    return rows


async def _fetch_broker_deal_records(account_alias: str):
    try:
        from account_manager import get_account_manager
    except ImportError:
        from scripts.account_manager import get_account_manager

    adapter = get_account_manager().get_adapter(account_alias)
    if not await adapter.authenticate():
        return []
    api = getattr(adapter, "api", None)
    stock_account = getattr(adapter, "stock_account", None) or getattr(api, "stock_account", None)
    if api is None or stock_account is None or not hasattr(api, "order_deal_records"):
        return []
    return api.order_deal_records(stock_account, timeout=10000) or []


def _merge_terminal_rows(orders: list[dict], terminal_rows: list[dict]) -> list[dict]:
    merged = orders
    for row in terminal_rows:
        merged = merge_open_orders(merged, row)
    return merged


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

    # Otherwise, keep orders but ensure minimal required keys, then remove any
    # order now visible as filled in broker deal records.
    orders = current.get("orders") if isinstance(current.get("orders"), list) else []
    account_alias = mode_state.get("default_account") or "sinopac_01"
    try:
        records = asyncio.run(_fetch_broker_deal_records(account_alias))
        terminal_rows = _deal_rows_from_records(orders, records)
        orders = _merge_terminal_rows(orders, terminal_rows)
    except Exception as exc:
        print(f"ORDERS_OPEN_BROKER_DEAL_SYNC_WARN: {type(exc).__name__}: {exc}")

    payload = build_orders_open_payload(orders, source=source or "live_broker")
    payload["effective_mode"] = "live-ready"
    ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ORDERS_OPEN_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
