#!/usr/bin/env python3
"""
ETF_TW Complete Trading CLI with Risk Control and Audit.

This is the complete trading interface that integrates:
- Multi-broker adapters
- Risk control checks
- Trade logging and audit
- Order execution

強制規則:
1. 正式送單一定走 skills/ETF_TW/.venv/bin/python
2. 交易時段硬閘門：非交易時段直接阻斷送單
3. preview / live submit 分開，不能互相覆蓋
"""

import asyncio
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

ROOT = Path(__file__).resolve().parents[1]

# Load private env if exists
ENV_FILE = ROOT / "private" / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v)

sys.path.append(str(ROOT))
from scripts.etf_core import context

try:
    from shioaji.constant import Unit
except Exception:
    Unit = None
from adapters import get_adapter
from trade_logger import get_logger, TradeLog
from risk_controller import get_risk_controller
from order_lifecycle import normalize_order_status, order_landed
from orders_open_state import build_orders_open_payload, merge_open_orders
from submit_verification import verification_payload
from trading_hours_gate import check_trading_hours_gate


ORDERS_OPEN_PATH = context.get_state_dir() / "orders_open.json"
GHOST_ORDERS_PATH = context.get_state_dir() / "ghost_orders.jsonl"


def load_orders_open() -> dict:
    if not ORDERS_OPEN_PATH.exists():
        return {"orders": [], "source": "live_broker"}
    return json.loads(ORDERS_OPEN_PATH.read_text(encoding="utf-8"))


def save_orders_open(rows: list[dict]) -> None:
    payload = build_orders_open_payload(rows, source="live_broker")
    ORDERS_OPEN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_submit_order_row(
    order_id: str,
    symbol: str,
    action: str,
    quantity: int,
    price: float | None,
    mode: str,
    account_id: str,
    broker_id: str,
    verified: bool,
    broker_order_id: str | None,
    broker_status: str | None,
) -> dict:
    normalized_broker_status = normalize_order_status(broker_status)
    return {
        "order_id": order_id,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "price": price,
        "mode": mode,
        "status": normalized_broker_status,
        "raw_status": broker_status,
        "source": "live_broker",
        "source_type": "submit_verification",
        "observed_at": datetime.now().astimezone().isoformat(),
        "verified": verified,
        "broker_order_id": broker_order_id,
        "broker_status": normalized_broker_status,
        "account": account_id,
        "broker_id": broker_id,
    }


def append_ghost_order(row: dict) -> None:
    GHOST_ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GHOST_ORDERS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


async def execute_trade(
    symbol: str,
    action: str,
    quantity: int,
    price: Optional[float],
    broker_id: str,
    account_id: str,
    mode: str = 'paper',
    decision_id: Optional[str] = None,
    suggested_price: Optional[float] = None,
):
    """
    Execute a complete trade with risk control and logging.

    Args:
        symbol: Stock/ETF symbol
        action: 'buy' or 'sell'
        quantity: Order quantity
        price: Order price (None for market order)
        broker_id: Broker identifier
        account_id: Account identifier
        mode: 'paper', 'sandbox', or 'live'
        decision_id: Link to the decision that triggered this trade (for EOD journal)
        suggested_price: The price suggested by decision engine (for slippage tracking)
    """
    # P4: 交易時段硬閘門 - 第一優先檢查
    if mode in ('live', 'sandbox'):
        print("=" * 72)
        print("🕒 交易時段檢查...")
        trading_session = check_trading_hours_gate()
        print(f"   ✓ 檢查通過：目前是 {trading_session} 時段")
        print("=" * 72)

    print("=" * 72)
    print(f"📈 執行交易：{action.upper()} {quantity} {symbol}")
    print("=" * 72)
    
    # Initialize components
    # Pass API keys from environment if available
    adapter_config = {
        'account_id': account_id,
        'mode': mode,
        'api_key': os.environ.get('SINOPAC_API_KEY'),
        'secret_key': os.environ.get('SINOPAC_SECRET_KEY'),
        'password': os.environ.get('SINOPAC_PASSWORD'),
    }
    adapter = get_adapter(broker_id, adapter_config)
    logger = get_logger()
    risk_ctrl = get_risk_controller()
    
    # Authenticate
    print(f"\n1. 認證 {broker_id}...")
    if not await adapter.authenticate():
        print("   ❌ 認證失敗")
        return
    
    print("   ✅ 认证成功")
    
    # Get market data
    print(f"\n2. 取得市場資料...")
    market_data = await adapter.get_market_data(symbol)
    current_price = price or market_data['price']
    print(f"   目前價格：{current_price}")
    
    # Risk control check
    print(f"\n3. 風險控制檢查...")
    try:
        balance = await adapter.get_account_balance(account_id)
        account_value = float(getattr(balance, 'total_value', 0) or getattr(balance, 'cash_available', 0) or 1000000)
    except Exception:
        account_value = 1000000

    risk_result = risk_ctrl.check_order(
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=current_price,
        current_position=0,
        account_value=account_value
    )
    
    if not risk_result.passed:
        print(f"   ❌ 風險檢查失敗：{risk_result.errors}")
        return
    
    if risk_result.warnings:
        print(f"   ⚠️ 警告：{risk_result.warnings}")
    
    if risk_result.requires_confirmation:
        print(f"   ⚠️ 需要確認：{risk_result.confirmation_reason}")
        confirm = input("   確定要繼續嗎？(y/n): ")
        if confirm.lower() != 'y':
            print("   已取消")
            return
    
    print("   ✅ 風險檢查通過")
    
    # Preview order
    print(f"\n4. 訂單預覽...")
    from adapters.base import Order
    order = Order(
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        account_id=account_id,
        broker_id=broker_id,
        mode=mode
    )
    
    preview = await adapter.preview_order(order)
    print(f"   預估費用：{preview.fee:.2f}")
    print(f"   預估稅額：{preview.tax:.2f}")
    
    # Submit order
    print(f"\n5. 送出訂單...")
    submitted_order = await adapter.submit_order(order)
    submitted_order.status = normalize_order_status(getattr(submitted_order, 'status', None))

    broker_order = None
    submitted_order_id = getattr(submitted_order, 'order_id', None)
    broker_order_id = getattr(submitted_order, 'broker_order_id', None)
    if submitted_order_id:
        try:
            broker_order = await adapter.get_order_status(submitted_order_id)
        except Exception:
            broker_order = None

    verify = verification_payload(submitted_order, broker_order)
    if broker_order_id and hasattr(adapter, "verify_order_landed"):
        try:
            landed_verify = await adapter.verify_order_landed(broker_order_id)
            verify["verified"] = bool(landed_verify.get("verified"))
            verify["broker_order_id"] = broker_order_id
            verify["broker_status"] = submitted_order.status if verify["verified"] else verify.get("broker_status")
        except Exception:
            verify["broker_order_id"] = broker_order_id

    # Fallback verification by live positions when broker order lookup is unavailable
    landed_by_position = False
    try:
        if mode != "live" and hasattr(adapter, 'get_positions'):
            positions = await adapter.get_positions(account_id)
            landed_by_position = any(str(getattr(pos, 'symbol', '')).split('.')[0] == symbol.split('.')[0] and int(getattr(pos, 'quantity', 0) or 0) >= quantity for pos in positions)
    except Exception:
        landed_by_position = False

    if mode == "live":
        landed = bool(verify["verified"])
    else:
        landed = verify['verified'] or landed_by_position or submitted_order.status in {'submitted', 'filled', 'partial_filled', 'cancelled', 'rejected', 'pending'}

    # Log the trade
    if landed:
        actual_order_id = submitted_order_id or broker_order_id
        logger.log_order_submitted(
            order_id=actual_order_id,
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            order_type=order.order_type,
            action=action,
            quantity=quantity,
            price=price
        )
        current_orders = load_orders_open().get("orders", [])
        order_row = build_submit_order_row(
            order_id=actual_order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            mode=mode,
            account_id=account_id,
            broker_id=broker_id,
            verified=verify["verified"],
            broker_order_id=verify["broker_order_id"],
            broker_status=verify["broker_status"],
        )
        # EOD Journal: embed decision_id + suggested_price for traceability
        if decision_id:
            order_row["decision_id"] = decision_id
        if suggested_price is not None:
            order_row["suggested_price"] = suggested_price
        save_orders_open(merge_open_orders(current_orders, order_row))
        if submitted_order.status == 'filled':
            logger.log_order_filled(
                order_id=actual_order_id,
                broker_id=broker_id,
                account_id=account_id,
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=submitted_order.filled_price,
                fee=submitted_order.fee,
                tax=submitted_order.tax
            )
            risk_ctrl.record_order(symbol, action, quantity, submitted_order.filled_price, 'filled')
            print("   ✅ 訂單已成交並記錄")
        elif submitted_order.status in {'cancelled', 'rejected'}:
            logger.log_order_rejected(
                order_id=actual_order_id,
                broker_id=broker_id,
                account_id=account_id,
                symbol=symbol,
                action=action,
                quantity=quantity,
                error=submitted_order.error
            )
            print(f"   ❌ 訂單被拒絕：{submitted_order.error}")
        else:
            print("   ✅ 訂單已送出並記錄")
    elif verify["verified"] and submitted_order.status == 'filled':
        logger.log_order_filled(
            order_id=submitted_order.order_id if hasattr(submitted_order, 'order_id') else 'order_001',
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=submitted_order.filled_price,
            fee=submitted_order.fee,
            tax=submitted_order.tax
        )
        risk_ctrl.record_order(symbol, action, quantity, submitted_order.filled_price, 'filled')
        print("   ✅ 訂單已成交並記錄")
    else:
        if mode == "live":
            append_ghost_order({
                "order_id": submitted_order_id,
                "broker_order_id": broker_order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "mode": mode,
                "ghost_detected_at": datetime.now().astimezone().isoformat(),
                "reason": "live_submit_unverified",
            })
        logger.log_order_rejected(
            order_id=submitted_order_id or broker_order_id or "",
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            error=submitted_order.error
        )
        print(f"   ❌ 訂單被拒絕：{submitted_order.error}")
    
    print(f"\n6. 最終狀態：{submitted_order.status.upper()}")
    print(f"   驗證結果：{'VERIFIED' if verify['verified'] else 'UNVERIFIED'}")
    if submitted_order.status == 'filled':
        print(f"   成交價格：{submitted_order.filled_price}")
        print(f"   成交數量：{submitted_order.filled_quantity}")
    
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description='ETF_TW Complete Trading CLI')
    parser.add_argument('symbol', help='Stock/ETF symbol (e.g., 0050.TW)')
    parser.add_argument('action', choices=['buy', 'sell'], help='Action')
    parser.add_argument('quantity', type=int, help='Quantity')
    parser.add_argument('--price', type=float, help='Limit price (optional)')
    parser.add_argument('--broker', default='sinopac', help='Broker ID')
    parser.add_argument('--account', default='sinopac_01', help='Account ID')
    parser.add_argument('--mode', default='live', choices=['paper', 'sandbox', 'live'], help='Trading mode')
    parser.add_argument('--decision-id', default=None, help='Decision ID linking to EOD journal')
    parser.add_argument('--suggested-price', type=float, default=None, help='Price suggested by decision engine')
    
    args = parser.parse_args()
    
    asyncio.run(execute_trade(
        symbol=args.symbol,
        action=args.action,
        quantity=args.quantity,
        price=args.price,
        broker_id=args.broker,
        account_id=args.account,
        mode=args.mode,
        decision_id=args.decision_id,
        suggested_price=args.suggested_price,
    ))


if __name__ == '__main__':
    main()
