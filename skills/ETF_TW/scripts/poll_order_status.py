#!/usr/bin/env python3
"""
ETF_TW Order Status Polling Script.
Polls specific orders at intervals until terminal status is reached or market closes.
"""

import asyncio
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from account_manager import get_account_manager
from trade_logger import get_logger
from order_lifecycle import normalize_order_status, order_terminal
from orders_open_state import build_orders_open_payload, merge_open_orders
from fills_ledger import load_fills_ledger as _load_fills_ledger, save_fills_ledger as _save_fills_ledger, merge_fill_facts
from scripts.etf_core import context
from scripts.truth_level import LEVEL_1_LIVE

ORDERS_OPEN_PATH = context.get_state_dir() / "orders_open.json"
FILLS_LEDGER_PATH = context.get_state_dir() / "fills_ledger.json"


def load_orders_open() -> dict:
    if not ORDERS_OPEN_PATH.exists():
        return {"orders": [], "source": "live_broker"}
    return json.loads(ORDERS_OPEN_PATH.read_text(encoding="utf-8"))


def save_orders_open(rows: list[dict]) -> None:
    payload = build_orders_open_payload(rows, source="live_broker")
    ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_fills_ledger() -> dict:
    return _load_fills_ledger(FILLS_LEDGER_PATH)


def save_fills_ledger(rows: list[dict]) -> None:
    _save_fills_ledger(FILLS_LEDGER_PATH, rows)


def build_polling_order_row(
    order_id: str,
    symbol: str | None,
    action: str | None,
    quantity: int,
    price: float | None,
    status: str,
) -> dict:
    normalized_status = normalize_order_status(status)
    return {
        "order_id": order_id,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "price": price,
        "mode": "live",
        "status": normalized_status,
        "raw_status": status,
        "source": "live_broker",
        "source_type": "broker_polling",
        "observed_at": datetime.now().astimezone().isoformat(),
        "verified": True,
        "broker_order_id": order_id,
        "broker_status": normalized_status,
        "_truth_level": LEVEL_1_LIVE,
    }


async def poll_order(order_id: str, broker_id: str, account_id: str, interval: int = 1800):
    """
    Poll an order status repeatedly.
    """
    manager = get_account_manager()
    adapter = manager.get_adapter(account_id)
    logger = get_logger()
    
    print(f"[*] Starting poll for Order ID: {order_id} (Interval: {interval}s)")
    
    while True:
        if not await adapter.authenticate():
            print("[!] Authentication failed during polling. Retrying next interval.")
            await asyncio.sleep(interval)
            continue
            
        # Get trades from broker
        trades = await adapter.get_trades(account_id)
        target_trade = next((t for t in trades if getattr(t, 'order_id', None) == order_id), None)
        
        if not target_trade:
            print(f"[-] Order {order_id} not found in recent trades.")
            # Depending on broker, it might have aged out or never reached the list
        else:
            status = normalize_order_status(getattr(target_trade, 'status', 'unknown'))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status.upper()}")

            current_orders = load_orders_open().get("orders", [])
            order_row = build_polling_order_row(
                order_id=order_id,
                symbol=getattr(target_trade, 'symbol', None),
                action=getattr(target_trade, 'action', None),
                quantity=getattr(target_trade, 'quantity', 0),
                price=getattr(target_trade, 'price', None) or getattr(target_trade, 'filled_price', None),
                status=status,
            )
            save_orders_open(merge_open_orders(current_orders, order_row))

            if order_row.get("status") in {"partial_filled", "filled"}:
                current_fills = load_fills_ledger().get("fills", [])
                save_fills_ledger(merge_fill_facts(current_fills, order_row))

            if order_terminal(target_trade):
                print(f"[+] Final status reached: {status.upper()}")
                # Log completion if filled
                if status == 'filled':
                    logger.log_order_filled(
                        order_id=order_id,
                        broker_id=broker_id,
                        account_id=account_id,
                        symbol=target_trade.symbol,
                        action=target_trade.action,
                        quantity=target_trade.quantity,
                        price=target_trade.filled_price,
                        fee=getattr(target_trade, 'fee', 0),
                        tax=getattr(target_trade, 'tax', 0)
                    )
                break

        # Check for market close (Simplified: hard check for 13:30 for TW)
        now = datetime.now()
        if now.hour == 13 and now.minute >= 35:
            print("[!] Market closed. Stopping poll.")
            break
            
        await asyncio.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description='ETF_TW Order Status Polling')
    parser.add_argument('order_id', help='Order ID to poll')
    parser.add_argument('--broker', default='sinopac', help='Broker ID')
    parser.add_argument('--account', default='sinopac_01', help='Account ID')
    parser.add_argument('--interval', type=int, default=1800, help='Polling interval in seconds (default 1800s/30m)')
    
    args = parser.parse_args()
    
    asyncio.run(poll_order(args.order_id, args.broker, args.account, args.interval))

if __name__ == '__main__':
    main()
