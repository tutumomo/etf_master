#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

LANDED_STATUSES = {"submitted", "partial_filled", "filled", "cancelled", "rejected"}
TERMINAL_STATUSES = {"filled", "cancelled", "rejected"}


def normalize_order_status(status: str | None) -> str:
    value = (status or "pending").strip().lower()
    alias_map = {
        "partially_filled": "partial_filled",
        "partial-filled": "partial_filled",
        "partial filled": "partial_filled",
    }
    value = alias_map.get(value, value)
    if value in {"failed", "error"}:
        return "rejected"
    if value in LANDED_STATUSES or value == "pending":
        return value
    return "pending"


def order_landed(order: Any) -> bool:
    order_id = getattr(order, "order_id", None)
    status = normalize_order_status(getattr(order, "status", None))
    return bool(order_id) and status in LANDED_STATUSES


def order_terminal(order: Any) -> bool:
    status = normalize_order_status(getattr(order, "status", None))
    return status in TERMINAL_STATUSES
