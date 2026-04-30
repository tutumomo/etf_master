#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any


def build_fill_fact_row(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("status") or "partial_filled"
    filled_quantity = row.get("filled_quantity")
    if filled_quantity is None and status == "filled":
        filled_quantity = row.get("quantity")
    return {
        "order_id": row.get("order_id"),
        "symbol": row.get("symbol"),
        "action": row.get("action"),
        "status": status,
        "filled_quantity": int(filled_quantity or 0),
        "remaining_quantity": row.get("remaining_quantity"),
        "price": row.get("price"),
        "source_type": row.get("source_type") or "broker_callback",
        "observed_at": row.get("observed_at") or datetime.now().astimezone().isoformat(),
    }


def build_fills_ledger_payload(rows: list[dict], source: str = "fill_facts") -> dict:
    return {
        "fills": rows,
        "updated_at": datetime.now().astimezone().isoformat(),
        "source": source,
    }


def merge_fill_facts(existing_rows: list[dict], new_row: dict[str, Any]) -> list[dict]:
    incoming = build_fill_fact_row(new_row)
    order_id = incoming.get("order_id")
    merged = []
    replaced = False

    for row in existing_rows:
        if order_id and row.get("order_id") == order_id:
            keep = dict(row)
            if int(incoming.get("filled_quantity") or 0) >= int(row.get("filled_quantity") or 0):
                keep.update(incoming)
            merged.append(keep)
            replaced = True
        else:
            merged.append(row)

    if not replaced:
        merged.append(incoming)

    return merged


def load_fills_ledger(path: Path) -> dict:
    if not path.exists():
        return {"fills": [], "source": "fill_facts"}
    return json.loads(path.read_text(encoding="utf-8"))


def save_fills_ledger(path: Path, rows: list[dict]) -> None:
    payload = build_fills_ledger_payload(rows, source="fill_facts")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
