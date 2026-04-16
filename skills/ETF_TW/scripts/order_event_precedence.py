#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from order_lifecycle import normalize_order_status, order_terminal


SOURCE_PRIORITY = {
    "broker_callback": 4,
    "broker_polling": 3,
    "submit_verification": 2,
    "submit_response": 1,
    "local_inference": 0,
}


def status_rank(status: str | None) -> int:
    normalized = normalize_order_status(status)
    rank = {
        "pending": 0,
        "submitted": 1,
        "partial_filled": 2,
        "filled": 3,
        "cancelled": 3,
        "rejected": 3,
    }
    return rank.get(normalized, 0)


def source_priority(source_type: str | None) -> int:
    return SOURCE_PRIORITY.get(source_type or "local_inference", 0)


def _parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def row_time(row: dict[str, Any]):
    return _parse_iso(row.get("event_time")) or _parse_iso(row.get("observed_at"))


def _merge_quantities(current: dict[str, Any], incoming: dict[str, Any], merged: dict[str, Any]) -> dict[str, Any]:
    current_filled = current.get("filled_quantity")
    incoming_filled = incoming.get("filled_quantity")
    if current_filled is not None or incoming_filled is not None:
        values = [v for v in [current_filled, incoming_filled] if v is not None]
        if values:
            merged["filled_quantity"] = max(int(v) for v in values)

    current_remaining = current.get("remaining_quantity")
    incoming_remaining = incoming.get("remaining_quantity")

    explicit_total = incoming.get("total_quantity")
    if explicit_total is None:
        explicit_total = current.get("total_quantity")

    if merged.get("filled_quantity") is not None and explicit_total is not None:
        merged["total_quantity"] = int(explicit_total)
        merged["remaining_quantity"] = max(int(explicit_total) - int(merged["filled_quantity"]), 0)
    elif current_remaining is not None or incoming_remaining is not None:
        values = [v for v in [current_remaining, incoming_remaining] if v is not None]
        if values:
            merged["remaining_quantity"] = min(int(v) for v in values)
    return merged


def choose_preferred_row(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    current_status = normalize_order_status(current.get("status"))
    incoming_status = normalize_order_status(incoming.get("status"))

    if order_terminal(type("Order", (), current)()) and not order_terminal(type("Order", (), incoming)()):
        return current
    if order_terminal(type("Order", (), incoming)()) and not order_terminal(type("Order", (), current)()):
        merged = dict(current)
        merged.update(incoming)
        return _merge_quantities(current, incoming, merged)

    current_rank = status_rank(current_status)
    incoming_rank = status_rank(incoming_status)
    if current_rank > incoming_rank:
        return current
    if incoming_rank > current_rank:
        merged = dict(current)
        merged.update(incoming)
        return _merge_quantities(current, incoming, merged)

    current_time = row_time(current)
    incoming_time = row_time(incoming)
    if current_time and incoming_time:
        if current_time > incoming_time:
            return current
        if incoming_time > current_time:
            merged = dict(current)
            merged.update(incoming)
            return _merge_quantities(current, incoming, merged)

    current_seq = current.get("broker_seq")
    incoming_seq = incoming.get("broker_seq")
    if current_seq is not None and incoming_seq is not None:
        if int(current_seq) > int(incoming_seq):
            return current
        if int(incoming_seq) > int(current_seq):
            merged = dict(current)
            merged.update(incoming)
            return _merge_quantities(current, incoming, merged)

    current_source = source_priority(current.get("source_type"))
    incoming_source = source_priority(incoming.get("source_type"))
    if current_source > incoming_source:
        return current

    merged = dict(current)
    merged.update(incoming)
    return _merge_quantities(current, incoming, merged)
