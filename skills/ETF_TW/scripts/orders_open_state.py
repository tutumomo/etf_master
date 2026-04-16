#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from order_lifecycle import normalize_order_status, order_terminal
from order_event_precedence import choose_preferred_row


def build_orders_open_payload(orders: list[dict], source: str = "live_broker", updated_at: str | None = None) -> dict:
    return {
        "orders": orders,
        "updated_at": updated_at or datetime.now().astimezone().isoformat(),
        "source": source,
    }


def normalize_open_order_row(row: dict[str, Any], source: str = "live_broker") -> dict[str, Any]:
    payload = dict(row)
    payload["status"] = normalize_order_status(payload.get("status"))
    payload["source"] = payload.get("source") or source
    if "verified" in payload:
        payload["verified"] = bool(payload.get("verified"))

    if payload.get("status") == "partial_filled":
        filled = payload.get("filled_quantity")
        total = payload.get("total_quantity")
        if filled is not None and total is not None:
            payload["remaining_quantity"] = max(int(total) - int(filled), 0)

    return payload


def merge_open_orders(existing_orders: list[dict], new_row: dict[str, Any]) -> list[dict]:
    normalized = normalize_open_order_row(new_row)
    order_id = normalized.get("order_id")
    merged = []
    replaced = False

    for row in existing_orders:
        current = normalize_open_order_row(row)
        if order_id and current.get("order_id") == order_id:
            merged.append(choose_preferred_row(current, normalized))
            replaced = True
        else:
            merged.append(current)

    if not replaced:
        merged.append(normalized)

    return [row for row in merged if not order_terminal(type("Order", (), row)())]
