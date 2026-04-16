#!/usr/bin/env python3
from __future__ import annotations

BROKER_FEE_RATE = 0.001425
ETF_SELL_TAX_RATE = 0.001


def estimate_fee(gross_amount: float) -> float:
    return max(round(gross_amount * BROKER_FEE_RATE, 2), 1.0)



def preview_order(order: dict, etf: dict) -> dict:
    quantity = float(order["quantity"])
    if order["order_type"] == "limit":
        price = float(order["price"])
    else:
        price = float(order.get("price") or 0)

    gross_amount = round(quantity * price, 2) if price > 0 else 0.0
    fee = estimate_fee(gross_amount) if gross_amount > 0 else 0.0
    tax = round(gross_amount * ETF_SELL_TAX_RATE, 2) if order["side"] == "sell" and gross_amount > 0 else 0.0
    total_cost = round(gross_amount + fee + tax, 2)
    cash_effect = total_cost if order["side"] == "buy" else round(gross_amount - fee - tax, 2)

    warnings: list[str] = []
    if etf["category"] in {"overseas-equity", "bond"}:
        warnings.append(f"{etf['symbol']} 屬於 {etf['category']}，新手下單前應先理解額外風險。")
    if "beginner" not in etf.get("suitable_for", []):
        warnings.append(f"{etf['symbol']} 不是明顯的 beginner/core 類型，請確認是否符合你的用途。")
    if order["order_type"] == "market":
        warnings.append("市價單預覽無法精準估算成交價格，金額僅供流程示意。")

    return {
        "symbol": etf["symbol"],
        "name": etf["name"],
        "side": order["side"],
        "order_type": order["order_type"],
        "lot_type": order["lot_type"],
        "quantity": quantity,
        "price_assumption": price,
        "estimated_gross_amount": gross_amount,
        "estimated_fee": fee,
        "estimated_tax": tax,
        "estimated_total_cost": total_cost,
        "estimated_cash_effect": cash_effect,
        "warnings": warnings,
    }
