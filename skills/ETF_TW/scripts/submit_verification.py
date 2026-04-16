#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from typing import Any

from scripts.truth_level import LEVEL_1_LIVE, LEVEL_2_VERIFYING
from scripts.order_lifecycle import normalize_order_status, order_landed


def verification_payload(submitted_order: Any, broker_order: Any | None) -> dict:
    submitted_status = normalize_order_status(getattr(submitted_order, "status", None))
    broker_status = normalize_order_status(getattr(broker_order, "status", None)) if broker_order else None
    submitted_order_id = getattr(submitted_order, "order_id", None)
    broker_order_id = getattr(broker_order, "order_id", None) if broker_order else None

    landed_by_submit = order_landed(submitted_order)
    landed_by_broker = order_landed(broker_order) if broker_order else False
    verified = bool(submitted_order_id) and bool(broker_order_id) and str(submitted_order_id) == str(broker_order_id)

    return {
        "submitted_order_id": submitted_order_id,
        "broker_order_id": broker_order_id,
        "submitted_status": submitted_status,
        "broker_status": broker_status,
        "landed_by_submit": landed_by_submit,
        "landed_by_broker": landed_by_broker,
        "verified": verified,
        "message": "[已落地]" if verified and landed_by_broker else "[驗證中] 委託已送出，仍需後續驗證（list_trades）確認落地事實",
        "_truth_level": LEVEL_1_LIVE if verified and landed_by_broker else LEVEL_2_VERIFYING,
    }


async def verify_order_landing(adapter: Any, order_id: str, timeout: int = 10) -> dict:
    """
    Automated post-submit verification to confirm the order has landed in the broker's system.
    
    Args:
        adapter: The broker adapter instance.
        order_id: The order ID to verify.
        timeout: Maximum time to wait for verification in seconds.
        
    Returns:
        dict: Verification result including status and truth level.
    """
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            # 優先使用 list_trades 獲取完整清單以驗證落地事實
            trades = await adapter.list_trades()
            for trade in trades:
                trade_id = getattr(trade, "order_id", None)
                if trade_id and str(trade_id) == str(order_id):
                    status = normalize_order_status(getattr(trade, "status", None))
                    # 只要出現在 list_trades 且不是 rejected，就視為已落地
                    if status != "rejected":
                        return {
                            "verified": True,
                            "order_id": order_id,
                            "status": status,
                            "message": f"[已落地] 委託 {order_id} 已在券商系統確認",
                            "_truth_level": LEVEL_1_LIVE,
                            "order": trade
                        }
        except Exception as e:
            # 靜默處理異常，繼續重試直到超時
            pass
            
        await asyncio.sleep(1)
        
    return {
        "verified": False,
        "order_id": order_id,
        "message": f"[未落地/待確認] 委託 {order_id} 已送出但券商端尚未於 {timeout} 秒內回報",
        "_truth_level": LEVEL_2_VERIFYING
    }
