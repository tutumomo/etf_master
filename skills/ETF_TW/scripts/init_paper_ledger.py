#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "paper_ledger.json"


def parse_position(value: str) -> dict:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("position must be SYMBOL,QUANTITY,PRICE,DATE")

    symbol, quantity_text, price_text, timestamp = parts
    if not symbol:
        raise ValueError("symbol is required")

    quantity = int(quantity_text)
    price = float(price_text)
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if price <= 0:
        raise ValueError("price must be positive")

    # Validate early and preserve the user's date as an ISO datetime string.
    if "T" in timestamp:
        parsed_ts = datetime.fromisoformat(timestamp)
    else:
        parsed_ts = datetime.fromisoformat(f"{timestamp}T00:00:00")

    return {
        "symbol": symbol.upper(),
        "quantity": quantity,
        "price": price,
        "timestamp": parsed_ts.isoformat(),
    }


def build_initial_trade(position: dict) -> dict:
    quantity = int(position["quantity"])
    price = float(position["price"])
    return {
        "symbol": str(position["symbol"]).upper(),
        "side": "buy",
        "quantity": quantity,
        "price": price,
        "estimated_total_cost": round(quantity * price, 2),
        "timestamp": position["timestamp"],
        "source": "initial_position",
    }


def build_initial_ledger(positions: list[dict], created_at: str | None = None) -> dict:
    return {
        "version": "1.0",
        "source": "manual_initialization",
        "created_at": created_at or datetime.now().isoformat(),
        "trades": [build_initial_trade(position) for position in positions],
    }


def write_initial_ledger(path: Path, ledger: dict, force: bool = False) -> None:
    if path.exists() and not force:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("trades"):
            raise FileExistsError(f"{path} already contains trades; use --force to overwrite")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize ETF_TW paper ledger from current holdings.")
    parser.add_argument(
        "--position",
        action="append",
        required=True,
        help="Initial position as SYMBOL,QUANTITY,PRICE,DATE, e.g. 006208,8,211.5,2026-04-29",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output ledger path")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing ledger with trades")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        positions = [parse_position(value) for value in args.position]
        ledger = build_initial_ledger(positions)
        write_initial_ledger(Path(args.output), ledger, force=args.force)
    except Exception as exc:
        print(f"PAPER_LEDGER_INIT_FAILED: {exc}")
        return 1

    print(f"PAPER_LEDGER_INIT_OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
