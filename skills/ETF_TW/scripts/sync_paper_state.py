#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

from trading_mode import read_trading_mode_state

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

LEDGER_PATH = ETF_TW_ROOT / "data" / "paper_ledger.json"
STATE_DIR = context.get_state_dir()
POSITIONS_STATE_PATH = STATE_DIR / "positions.json"
ACCOUNT_STATE_PATH = STATE_DIR / "account_snapshot.json"
ORDERS_OPEN_STATE_PATH = STATE_DIR / "orders_open.json"


def build_positions_from_trades(trades: list[dict]) -> list[dict]:
    holdings: dict[str, dict] = {}

    for t in trades:
        symbol = t.get("symbol")
        if not symbol:
            continue

        qty = int(t.get("quantity") or 0)
        total_cost = float(t.get("estimated_total_cost") or 0)
        side = t.get("side")

        if symbol not in holdings:
            holdings[symbol] = {
                "symbol": symbol,
                "quantity": 0,
                "total_cost": 0.0,
                "source": "paper_ledger",
            }

        if side == "buy":
            holdings[symbol]["quantity"] += qty
            holdings[symbol]["total_cost"] += total_cost
        elif side == "sell":
            current_qty = holdings[symbol]["quantity"]
            current_cost = holdings[symbol]["total_cost"]
            if current_qty > 0 and qty > 0:
                avg_cost = current_cost / current_qty
                reduce_qty = min(qty, current_qty)
                holdings[symbol]["quantity"] -= reduce_qty
                holdings[symbol]["total_cost"] -= avg_cost * reduce_qty

    results = []
    for symbol, item in holdings.items():
        if item["quantity"] <= 0:
            continue
        avg_cost = item["total_cost"] / item["quantity"] if item["quantity"] else 0.0
        results.append({
            "symbol": symbol,
            "quantity": item["quantity"],
            "average_cost": round(avg_cost, 4),
            "total_cost": round(item["total_cost"], 2),
            "source": item["source"],
        })

    results.sort(key=lambda x: x["symbol"])
    return results


def build_account_snapshot(positions: list[dict]) -> dict:
    market_value = round(sum(float(p.get("total_cost") or 0) for p in positions), 2)
    return {
        "cash": 0,
        "market_value": market_value,
        "total_equity": market_value,
        "updated_at": datetime.now().isoformat(),
        "source": "paper_ledger",
        "position_count": len(positions),
    }


def main() -> int:
    mode_state = read_trading_mode_state()
    if mode_state.get("effective_mode") == "live-ready":
        print("PAPER_STATE_SYNC_SKIPPED_LIVE_READY")
        return 0

    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    trades = payload.get("trades", [])
    positions = build_positions_from_trades(trades)
    account = build_account_snapshot(positions)

    POSITIONS_STATE_PATH.write_text(json.dumps({
        "positions": positions,
        "updated_at": account["updated_at"],
        "source": "paper_ledger",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ACCOUNT_STATE_PATH.write_text(json.dumps(account, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ORDERS_OPEN_STATE_PATH.write_text(json.dumps({
        "orders": [],
        "updated_at": account["updated_at"],
        "source": "paper_ledger",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PAPER_STATE_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
