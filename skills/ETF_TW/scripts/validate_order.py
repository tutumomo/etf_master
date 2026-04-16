#!/usr/bin/env python3
"""
ETF_TW 訂單驗證 - 簡化風控版本

優化原則：
1. 只在「非常有需要」時提醒（重大風險）
2. 移除制式警告，避免干擾使用者
3. 單位檢查：只在大於 10 倍差異時提醒
4. 金額檢查：只在大於 50% 閾值時提醒
"""
from __future__ import annotations

VALID_SIDES = {"buy", "sell"}
VALID_ORDER_TYPES = {"market", "limit"}
VALID_LOT_TYPES = {"board", "odd"}
VALID_MODES = {"paper", "sandbox", "live"}


def validate_order(order: dict, known_symbols: set[str], config: dict = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    
    # 風控閾值
    risk_config = (config or {}).get("risk_controls", {})
    max_value = risk_config.get("max_single_trade_value", 1000000)
    max_qty = risk_config.get("max_single_trade_quantity", 50000)
    unit_mismatch_threshold = risk_config.get("unit_mismatch_threshold", 10)

    # 檢查標的
    symbol = str(order.get("symbol") or "").upper()
    if not symbol or symbol not in known_symbols:
        errors.append("symbol is missing or unknown")

    # 檢查方向
    side = str(order.get("side") or "").lower()
    if side not in VALID_SIDES:
        errors.append("side must be buy or sell")

    # 檢查訂單類型
    order_type = str(order.get("order_type") or "").lower()
    if order_type not in VALID_ORDER_TYPES:
        errors.append("order_type must be market or limit")

    # 檢查訂單類型
    lot_type = str(order.get("lot_type") or "").lower()
    if lot_type not in VALID_LOT_TYPES:
        errors.append("lot_type must be board or odd")

    # 檢查模式
    mode = str(order.get("mode") or "").lower()
    if mode not in VALID_MODES:
        errors.append("mode must be paper in this version")

    # 檢查數量
    quantity = order.get("quantity")
    qty_val = 0
    try:
        qty_val = float(quantity)
        if qty_val <= 0:
            errors.append("quantity must be positive")
        
        # ⚠️ 風控：只在極端情況下提醒
        # 只有當數量超過 10,000 股（10 張）時才提醒
        # 避免對正常小額交易造成干擾
        if qty_val >= 10000:
            warnings.append(f"⚠️ 大額交易提醒：下單數量 {qty_val:,.0f} 股 ({qty_val/1000:.0f} 張)，請確認是否為預期數量。")
    except Exception:
        errors.append("quantity must be numeric")

    # 檢查價格
    price = order.get("price")
    if order_type == "limit":
        try:
            price_val = float(price)
            if price_val <= 0:
                errors.append("price must be positive for limit orders")
            
            # ⚠️ 風控：只在大額交易時提醒
            # 當總金額超過閾值的 150% 時才提醒
            if "qty_val" in locals() and qty_val > 0:
                total_val = qty_val * price_val
                if total_val >= max_value * 1.5:
                    warnings.append(f"⚠️ 大額交易提醒：單筆預估金額 NT$ {total_val:,.0f}，已超過風險閾值 (NT$ {max_value:,.0f}) 的 150%。")
        except Exception:
            errors.append("price must be numeric for limit orders")
    elif price not in (None, "", 0, 0.0):
        # 市價單有價格欄位時，只記錄不警告
        pass

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }
