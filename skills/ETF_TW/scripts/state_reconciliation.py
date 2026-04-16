#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def symbol_set(rows: list[dict], key: str = "symbol") -> set[str]:
    return {row.get(key) for row in rows if row.get(key)}


def stale_delta_seconds(newer_ts: str | None, older_ts: str | None) -> float | None:
    newer = parse_iso(newer_ts)
    older = parse_iso(older_ts)
    if not newer or not older:
        return None
    return (newer - older).total_seconds()


def reconciliation_summary(positions_payload: dict, snapshot_payload: dict, orders_open_payload: dict) -> dict[str, Any]:
    position_symbols = symbol_set(positions_payload.get("positions", []))
    holding_symbols = symbol_set(snapshot_payload.get("holdings", []))
    open_symbols = symbol_set(orders_open_payload.get("orders", []))

    snapshot_lag_sec = stale_delta_seconds(snapshot_payload.get("updated_at"), positions_payload.get("updated_at"))

    return {
        "positions_vs_snapshot_match": position_symbols == holding_symbols,
        "position_symbols": sorted(position_symbols),
        "holding_symbols": sorted(holding_symbols),
        "open_order_symbols": sorted(open_symbols),
        "open_orders_not_in_positions": sorted(open_symbols - position_symbols),
        "open_orders_not_in_snapshot": sorted(open_symbols - holding_symbols),
        "snapshot_lag_sec": snapshot_lag_sec,
    }
