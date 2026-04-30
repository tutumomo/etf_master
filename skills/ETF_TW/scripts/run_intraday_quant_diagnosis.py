#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.etf_core import context
from scripts.etf_core.state_io import atomic_save_json, safe_load_json

TW_TZ = ZoneInfo("Asia/Taipei")


def _items_by_symbol(rows: list[dict]) -> dict[str, dict]:
    return {
        str(row.get("symbol") or "").upper(): row
        for row in rows
        if row.get("symbol")
    }


def _symbol_set(watchlist: dict, positions: dict) -> list[str]:
    symbols: set[str] = set()
    for item in watchlist.get("items", []):
        if item.get("symbol"):
            symbols.add(str(item["symbol"]).upper())
    for item in positions.get("positions", []):
        if item.get("symbol"):
            symbols.add(str(item["symbol"]).upper())
    return sorted(symbols)


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_intraday_quant_diagnosis(state_dir: Path) -> dict:
    market_cache = safe_load_json(state_dir / "market_cache.json", {"quotes": {}})
    watchlist = safe_load_json(state_dir / "watchlist.json", {"items": []})
    positions = safe_load_json(state_dir / "positions.json", {"positions": []})
    tape = safe_load_json(state_dir / "intraday_tape_context.json", {"watchlist_signals": []})

    quotes = market_cache.get("quotes", {})
    position_by_symbol = _items_by_symbol(positions.get("positions", []))
    watch_by_symbol = _items_by_symbol(watchlist.get("items", []))
    tape_by_symbol = _items_by_symbol(tape.get("watchlist_signals", []))

    rows = []
    missing_quotes = []
    for symbol in _symbol_set(watchlist, positions):
        quote = quotes.get(symbol, {})
        price = _float(quote.get("current_price"))
        prev_close = _float(quote.get("prev_close"))
        open_price = _float(quote.get("open"))
        change_pct = quote.get("change_pct")
        if change_pct is None and price > 0 and prev_close > 0:
            change_pct = (price - prev_close) / prev_close * 100

        if price <= 0:
            missing_quotes.append(symbol)

        position = position_by_symbol.get(symbol, {})
        watch = watch_by_symbol.get(symbol, {})
        tape_row = tape_by_symbol.get(symbol, {})

        avg_price = _float(position.get("average_price"))
        quantity = _float(position.get("quantity"))
        unrealized_pct = ((price - avg_price) / avg_price * 100) if price > 0 and avg_price > 0 else None
        intraday_pct = ((price - open_price) / open_price * 100) if price > 0 and open_price > 0 else None

        rows.append({
            "symbol": symbol,
            "name": watch.get("name") or position.get("name") or symbol,
            "group": watch.get("group") or watch.get("category") or position.get("group") or "unknown",
            "in_position": quantity > 0,
            "quantity": int(quantity) if quantity.is_integer() else quantity,
            "current_price": round(price, 4),
            "change_pct": round(_float(change_pct), 2) if change_pct is not None else None,
            "intraday_return_pct": round(intraday_pct, 2) if intraday_pct is not None else None,
            "unrealized_return_pct": round(unrealized_pct, 2) if unrealized_pct is not None else None,
            "relative_strength": tape_row.get("relative_strength", "unknown"),
            "tape_label": tape_row.get("tape_label", "資料不足" if price <= 0 else "未分類"),
            "source": quote.get("source") or "market_cache",
        })

    positioned = [row for row in rows if row["in_position"]]
    watch_only = [row for row in rows if not row["in_position"]]
    avg_change = (
        sum(row["change_pct"] for row in rows if row["change_pct"] is not None)
        / max(len([row for row in rows if row["change_pct"] is not None]), 1)
    )

    return {
        "updated_at": datetime.now(TW_TZ).isoformat(),
        "source": "ETF_TW.run_intraday_quant_diagnosis",
        "symbol_count": len(rows),
        "position_count": len(positioned),
        "watch_only_count": len(watch_only),
        "average_change_pct": round(avg_change, 2),
        "missing_quotes": missing_quotes,
        "rows": rows,
    }


def main() -> int:
    state_dir = context.get_state_dir()
    payload = build_intraday_quant_diagnosis(state_dir)
    atomic_save_json(state_dir / "intraday_quant_diagnosis.json", payload)
    print(
        "INTRADAY_QUANT_DIAGNOSIS_OK "
        f"symbols={payload['symbol_count']} positions={payload['position_count']} "
        f"missing_quotes={len(payload['missing_quotes'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
