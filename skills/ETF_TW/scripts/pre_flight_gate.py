#!/usr/bin/env python3
"""
Pre-flight Gate for ETF_TW.
Unified validation logic for all trading paths.
"""

import os
import json
from typing import Dict, Any, Optional
from .sizing_engine_v1 import calculate_size
from .trading_hours_gate import get_trading_hours_info

def load_safety_data() -> Dict[str, Any]:
    """載入安全紅線與日損益數據"""
    from .etf_core import context
    state_dir = context.get_state_dir()
    redlines_file = state_dir / "safety_redlines.json"
    daily_pnl_file = state_dir / "daily_pnl.json"

    def safe_load(path, default):
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    return {
        "redlines": safe_load(redlines_file, {"enabled": False}),
        "pnl": safe_load(daily_pnl_file, {"circuit_breaker_triggered": False})
    }


def check_order(order: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    統一的下單前檢查閘門（累積式檢查版本）。
    """
    symbol = order.get('symbol', '').upper()
    side = order.get('side', '').lower()
    quantity = order.get('quantity', 0)
    price = order.get('price', 0.0)
    order_type = order.get('order_type', 'limit').lower()
    
    errors = []
    
    # 1. 基本參數檢查
    if not symbol: return {'passed': False, 'reason': '缺失標的代號', 'details': {}}
    if side not in ['buy', 'sell']: return {'passed': False, 'reason': f'不合法的交易方向: {side}', 'details': {}}
    if quantity <= 0: errors.append(f"委託數量必須大於 0 (目前: {quantity})")
    if order_type == 'limit' and price <= 0: errors.append(f"限價單價格必須大於 0 (目前: {price})")

    if errors: return {'passed': False, 'reason': " | ".join(errors), 'details': {}}

    # 2. Safety Redlines (絕對紅線) 檢查
    safety_data = load_safety_data()
    redlines = safety_data['redlines']
    pnl = safety_data['pnl']

    if redlines.get('enabled', True):
        # 2.1 日損益熔斷器
        if side == 'buy' and pnl.get('circuit_breaker_triggered', False):
            errors.append("已觸發日損益熔斷保護，禁止買入")

        # 2.2 買入限制檢查
        if side == 'buy':
            order_amount = quantity * price
            cash = context.get('cash', 0.0)

            # 金額絕對上限
            max_amount_twd = redlines.get('max_buy_amount_twd', 500000.0)
            if order_amount > max_amount_twd:
                errors.append(f"單筆金額 NT$ {order_amount:,.0f} 超過安全紅線 NT$ {max_amount_twd:,.0f}")

            # 股數絕對上限
            max_shares = redlines.get('max_buy_shares', 1000)
            if quantity > max_shares:
                errors.append(f"單筆股數 {quantity} 股 超過安全紅線 {max_shares} 股")

            # 個股集中度上限
            inventory = context.get('inventory', {})
            total_portfolio_value = context.get('total_portfolio_value') or (cash + sum(qty * price for s, qty in inventory.items()))
            max_conc_pct = redlines.get('max_concentration_pct', 30.0)
            
            # 修復：確保即使持倉為0，計算也不會混亂
            current_holding_shares = float(inventory.get(symbol, 0))
            target_weight = ((current_holding_shares + quantity) * price / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
            
            if target_weight > max_conc_pct:
                errors.append(f"預計持倉權重 {target_weight:.1f}% (當前{current_holding_shares}股 + 委託{quantity}股) 超過集中度紅線 {max_conc_pct}% (資產總值: {total_portfolio_value:,.0f})")

            # AI 信心門檻
            ai_conf = order.get('ai_confidence')
            if ai_conf is not None:
                threshold = redlines.get('ai_confidence_threshold', 0.7)
                conf_val = {"high": 0.9, "medium": 0.7, "low": 0.5}.get(str(ai_conf).lower(), float(ai_conf)) if isinstance(ai_conf, str) else float(ai_conf)
                if conf_val < threshold:
                    errors.append(f"AI 決策信心度 {conf_val} 低於要求的門檻 {threshold}")

    # 3. 交易時段與單位檢查
    force_hours = context.get('force_trading_hours', True)
    if force_hours:
        from .trading_hours_gate import get_trading_hours_info
        hours_info = get_trading_hours_info()
        if not hours_info['is_trading_hours']:
            errors.append(f"非交易時段 ({hours_info.get('reason', '市場未開盤')})")

    # 最終結果回傳
    if errors:
        return {
            'passed': False,
            'reason': "；".join(errors),
            'details': {'error_count': len(errors)}
        }

    return {'passed': True, 'reason': '已通過所有安全紅線檢查', 'details': {}}

if __name__ == "__main__":
    test_context = {'cash': 1000000, 'inventory': {}, 'risk_temperature': 1.0}
    
    print("--- Test 1: Amount Limit ---")
    order1 = {'symbol': '0050', 'side': 'buy', 'quantity': 10000, 'price': 100} # 1,000,000 > 500,000
    print(f"Order: {order1}")
    print(f"Result: {check_order(order1, test_context)}")
    
    print("\n--- Test 2: Shares Limit ---")
    order2 = {'symbol': '0050', 'side': 'buy', 'quantity': 500, 'price': 100} # 500 > 200
    print(f"Order: {order2}")
    print(f"Result: {check_order(order2, test_context)}")
    
    print("\n--- Test 3: AI Confidence Limit ---")
    order3 = {'symbol': '0050', 'side': 'buy', 'quantity': 100, 'price': 100, 'ai_confidence': 0.5} # 0.5 < 0.7
    print(f"Order: {order3}")
    print(f"Result: {check_order(order3, test_context)}")

    print("\n--- Test 4: OK Order ---")
    order4 = {'symbol': '0050', 'side': 'buy', 'quantity': 100, 'price': 100, 'ai_confidence': 0.8}
    print(f"Order: {order4}")
    print(f"Result: {check_order(order4, test_context)}")
