#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from order_lifecycle import normalize_order_status


def event_payload_to_order_row(event_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    order_id = payload.get("order_id")
    if not order_id:
        return None

    event_status_map = {
        "status_update": payload.get("status"),
        "cancel_requested": "cancelled",
        "order_submitted": "submitted",
        "order_filled": "filled",
        "order_cancelled": "cancelled",
        "order_rejected": "rejected",
    }
    status = normalize_order_status(event_status_map.get(event_type) or payload.get("status"))

    row = {
        "order_id": order_id,
        "symbol": payload.get("symbol"),
        "action": payload.get("action"),
        "quantity": int(payload.get("quantity") or 0),
        "price": payload.get("price"),
        "mode": payload.get("mode") or "live",
        "status": status,
        "raw_status": str(event_status_map.get(event_type) or payload.get("status") or status).lower(),
        "source": payload.get("source") or "live_broker",
        "source_type": payload.get("source_type") or "broker_callback",
        "observed_at": payload.get("observed_at") or datetime.now().astimezone().isoformat(),
        "event_time": payload.get("event_time"),
        "verified": True,
        "broker_order_id": order_id,
        "broker_status": status,
        "broker_seq": payload.get("broker_seq") or payload.get("seqno"),
        "account": payload.get("account"),
        "broker_id": payload.get("broker_id"),
    }
    if payload.get("filled_quantity") is not None:
        row["filled_quantity"] = int(payload.get("filled_quantity"))
    if payload.get("remaining_quantity") is not None:
        row["remaining_quantity"] = int(payload.get("remaining_quantity"))
    if payload.get("total_quantity") is not None:
        row["total_quantity"] = int(payload.get("total_quantity"))
    return row
