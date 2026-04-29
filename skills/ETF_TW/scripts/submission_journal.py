#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from etf_core.state_io import safe_append_jsonl
except ImportError:
    from scripts.etf_core.state_io import safe_append_jsonl


JOURNAL_FILENAME = "submission_journal.jsonl"


def append_submission_journal(state_dir: Path, event: dict[str, Any]) -> Path:
    """Append one live submission audit event without changing trading state."""
    payload = dict(event)
    payload.setdefault("observed_at", datetime.now().astimezone().isoformat())
    payload.setdefault("source", "live_submit_sop")
    return safe_append_jsonl(state_dir / JOURNAL_FILENAME, payload)


def build_submit_response_row(order: dict[str, Any], submitted: Any, observed_at: str | None = None) -> dict[str, Any]:
    """Normalize adapter submit response metadata before broker verification."""
    broker_order_id = str(getattr(submitted, "broker_order_id", "") or "")
    raw_status = str(getattr(submitted, "status", "") or "submitted").lower()
    return {
        "event": "submit_response",
        "source_type": "submit_response",
        "raw_status": raw_status,
        "status": raw_status,
        "observed_at": observed_at or datetime.now().astimezone().isoformat(),
        "order_id": order.get("order_id", ""),
        "broker_order_id": broker_order_id,
        "symbol": order.get("symbol"),
        "action": order.get("side") or order.get("action"),
        "quantity": order.get("quantity"),
        "price": order.get("price"),
        "lot_type": order.get("lot_type"),
        "mode": "live",
        "account": order.get("account_id") or order.get("account"),
        "broker_id": order.get("broker_id") or order.get("broker"),
        "verified": False,
        "landed": False,
    }
