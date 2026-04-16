#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    # Python 3.9 compatibility
    from datetime import timezone as UTC
from pathlib import Path


def execute_paper_trade(order: dict, preview: dict, ledger_path: Path) -> dict:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    trade = {
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "mode": "paper",
        "symbol": order["symbol"],
        "side": order["side"],
        "order_type": order["order_type"],
        "lot_type": order["lot_type"],
        "quantity": order["quantity"],
        "price": order.get("price"),
        "estimated_total_cost": preview["estimated_total_cost"],
        "estimated_cash_effect": preview["estimated_cash_effect"],
        "warnings": preview["warnings"],
    }
    payload.setdefault("trades", []).append(trade)
    ledger_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return trade
