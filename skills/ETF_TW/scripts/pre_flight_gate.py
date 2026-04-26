#!/usr/bin/env python3
"""
Pre-flight Gate for ETF_TW.
Unified validation logic for all trading paths.

Check order (fail-fast, priority-ordered):
  1. Trading hours gate (if force_trading_hours=True)
  2. Basic params: symbol, side, quantity > 0, price > 0
  3. Lot-type unit rules: board=multiple of 1000, odd=1-999
  4. Inventory check (sell side)
  5. Sizing limit (cash * max_concentration_pct)
  6. Safety redlines (absolute caps from safety_redlines.json)
  7. Confirm flag (is_submit=True requires is_confirmed=True)

Each check returns a machine-readable reason code on failure.
"""

import json
from typing import Dict, Any
from .trading_hours_gate import get_trading_hours_info
from .daily_order_limits import default_daily_order_limits


def load_safety_data(state_dir_override=None) -> Dict[str, Any]:
    """載入安全紅線與日損益數據"""
    from .etf_core import context
    state_dir = state_dir_override or context.get_state_dir()
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

    redlines = safe_load(redlines_file, {"enabled": True})
    redlines["enabled"] = True
    return {
        "redlines": redlines,
        "pnl": safe_load(daily_pnl_file, {"circuit_breaker_triggered": False}),
    }


def load_daily_order_limits(state_dir) -> Dict[str, Any]:
    """讀取當日送單配額狀態，不在 gate 層寫入狀態。"""
    limits_file = state_dir / "daily_order_limits.json"
    try:
        with open(limits_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_daily_order_limits()

    default_data = default_daily_order_limits()
    if data.get("date") != default_data["date"]:
        return default_data
    return {
        "date": data.get("date", default_data["date"]),
        "buy_submit_count": int(data.get("buy_submit_count", 0)),
        "sell_submit_count": int(data.get("sell_submit_count", 0)),
        "last_updated": data.get("last_updated", default_data["last_updated"]),
    }


def _fail(reason: str, details: dict = None) -> Dict[str, Any]:
    return {'passed': False, 'reason': reason, 'details': details or {}}


def _pass(details: dict = None) -> Dict[str, Any]:
    return {'passed': True, 'reason': '', 'details': details or {}}


def compute_investment_score(order: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    計算投資評分（-10 ~ +10），不影響通過/攔截邏輯，僅供 dashboard 參考顯示。

    因子：
      AI 信心 high +3 / medium +1 / low -2
      策略對齊 strategy_aligned=True +2
      規模合理 order_amount < cash * 0.15 +2
      規模偏高 order_amount > cash * 0.25 -2
      正常交易時段 +1
      市場 regime cautious -2 / bullish +1
    """
    score = 0
    breakdown: list[str] = []

    # AI 信心
    ai_conf = order.get('ai_confidence')
    if ai_conf is not None:
        conf_label = str(ai_conf).lower()
        if conf_label == 'high':
            score += 3
            breakdown.append('AI信心:high +3')
        elif conf_label == 'medium':
            score += 1
            breakdown.append('AI信心:medium +1')
        elif conf_label == 'low':
            score -= 2
            breakdown.append('AI信心:low -2')

    # 策略對齊
    if context.get('strategy_aligned'):
        score += 2
        breakdown.append('策略對齊 +2')

    # 規模比例
    cash = context.get('cash', 0.0)
    price = order.get('price', 0.0)
    quantity = order.get('quantity', 0)
    if cash > 0 and price > 0 and quantity > 0:
        order_amount = quantity * price
        ratio = order_amount / cash
        if ratio < 0.15:
            score += 2
            breakdown.append(f'規模合理({ratio:.0%}<15%) +2')
        elif ratio > 0.25:
            score -= 2
            breakdown.append(f'規模偏高({ratio:.0%}>25%) -2')

    # 交易時段
    try:
        hours_info = get_trading_hours_info()
        if hours_info.get('is_trading_hours'):
            score += 1
            breakdown.append('正常交易時段 +1')
    except Exception:
        pass

    # 市場 regime
    market_regime = str(context.get('market_regime', '')).lower()
    if 'cautious' in market_regime:
        score -= 2
        breakdown.append('市場cautious -2')
    elif 'bullish' in market_regime:
        score += 1
        breakdown.append('市場bullish +1')

    score = max(-10, min(10, score))
    return {'investment_score': score, 'score_breakdown': breakdown}


def check_order(order: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    統一的下單前檢查閘門（fail-fast 優先序版本）。
    每個檢查點獨立回傳 machine-readable reason code。
    """
    symbol   = order.get('symbol', '').upper()
    side     = order.get('side', '').lower()
    quantity = order.get('quantity', 0)
    price    = order.get('price', 0.0)
    lot_type = order.get('lot_type', '')          # 'board' | 'odd' | ''
    is_submit    = order.get('is_submit', False)
    is_confirmed = order.get('is_confirmed', False)
    order_type   = order.get('order_type', 'limit').lower()

    # ── 1. 交易時段檢查 ─────────────────────────────────────────────────────
    force_hours = context.get('force_trading_hours', True)
    if force_hours:
        hours_info = get_trading_hours_info()
        if not hours_info.get('is_trading_hours', False):
            return _fail('outside_trading_hours', {'time': hours_info.get('current_time')})

    # ── 2. 基本參數檢查 ──────────────────────────────────────────────────────
    if not symbol:
        return _fail('missing_symbol')
    if side not in ('buy', 'sell'):
        return _fail('invalid_side', {'side': side})
    if not isinstance(quantity, (int, float)) or quantity <= 0:
        return _fail('invalid_quantity', {'quantity': quantity})
    if order_type == 'limit' and (not isinstance(price, (int, float)) or price <= 0):
        return _fail('invalid_price', {'price': price})

    # ── 3. 單位格式檢查 ──────────────────────────────────────────────────────
    if lot_type == 'board':
        if quantity % 1000 != 0:
            return _fail('invalid_unit_for_board_lot', {'quantity': quantity, 'rule': 'multiple of 1000'})
    elif lot_type == 'odd':
        if not (1 <= quantity <= 999):
            return _fail('invalid_unit_for_odd_lot', {'quantity': quantity, 'rule': '1-999'})

    # ── 4. 庫存檢查（賣出）──────────────────────────────────────────────────
    if side == 'sell':
        inventory = context.get('inventory', {})
        held = inventory.get(symbol, inventory.get(symbol.replace('.TW', '').replace('.TWO', ''), 0))
        if quantity > held:
            return _fail('insufficient_inventory', {'held': held, 'requested': quantity})

    # ── 5. Sizing Limit（買入）──────────────────────────────────────────────
    if side == 'buy':
        cash = context.get('cash', 0.0)
        # 優先使用「可交割金額」(settlement_safe_cash = cash 扣除 T+1/T+2 淨額)
        # 若 context 未提供或為 0，fallback 到帳面現金
        settlement_safe_cash = context.get('settlement_safe_cash')
        sizing_base = settlement_safe_cash if (settlement_safe_cash is not None and settlement_safe_cash > 0) else cash
        max_conc = context.get('max_concentration_pct')
        max_single = context.get('max_single_limit_twd')

        if max_conc is not None and sizing_base > 0:
            allowed_amount = sizing_base * max_conc
            allowed_shares = int(allowed_amount // price) if price > 0 else 0
            # Round down to nearest board lot if lot_type is board
            if lot_type == 'board' and allowed_shares >= 1000:
                allowed_shares = (allowed_shares // 1000) * 1000
            if quantity > allowed_shares:
                return _fail('exceeds_sizing_limit', {
                    'allowed': allowed_shares,
                    'requested': quantity,
                    'max_amount_twd': allowed_amount,
                    'sizing_base': 'settlement_safe_cash' if (settlement_safe_cash is not None and settlement_safe_cash > 0) else 'cash',
                })

        if max_single is not None and price > 0:
            order_amount = quantity * price
            if order_amount > max_single:
                return _fail('exceeds_sizing_limit', {
                    'allowed': int(max_single // price),
                    'requested': quantity,
                    'max_amount_twd': max_single,
                })

    # ── 6. 確認旗標（三段式送單）── 必須在安全紅線前，讓 UI 流程優先被檢查 ──
    if is_submit and not is_confirmed:
        return _fail('missing_confirm_flag')

    # ── 7. Safety Redlines（安全紅線）────────────────────────────────────────
    # context 可設 _skip_safety_redlines=True 供測試環境跳過檔案紅線
    if context.get('_skip_safety_redlines'):
        score_result = compute_investment_score(order, context)
        result = _pass()
        result['investment_score'] = score_result['investment_score']
        result['score_breakdown'] = score_result['score_breakdown']
        return result

    try:
        state_dir = context.get("state_dir")
        safety_data = load_safety_data(state_dir_override=state_dir)
        redlines = safety_data['redlines']
        pnl      = safety_data['pnl']
        daily_order_limits = load_daily_order_limits(state_dir) if state_dir else default_daily_order_limits()

        if True:
            daily_max_buy_submits = int(redlines.get('daily_max_buy_submits', 2))
            daily_max_sell_submits = int(redlines.get('daily_max_sell_submits', 2))

            if side == 'buy' and daily_order_limits.get('buy_submit_count', 0) >= daily_max_buy_submits:
                return _fail('daily_buy_submit_quota_exceeded', {
                    'limit': daily_max_buy_submits,
                    'used': daily_order_limits.get('buy_submit_count', 0),
                })

            if side == 'sell' and daily_order_limits.get('sell_submit_count', 0) >= daily_max_sell_submits:
                return _fail('daily_sell_submit_quota_exceeded', {
                    'limit': daily_max_sell_submits,
                    'used': daily_order_limits.get('sell_submit_count', 0),
                })

            # 日損益熔斷
            if side == 'buy' and pnl.get('circuit_breaker_triggered', False):
                return _fail('circuit_breaker_triggered')

            if side == 'buy' and price > 0:
                order_amount = quantity * price

                # 金額絕對上限
                max_amount_twd = redlines.get('max_buy_amount_twd', 500_000.0)
                if order_amount > max_amount_twd:
                    return _fail('redline_amount_exceeded', {
                        'order_amount': order_amount,
                        'max_amount_twd': max_amount_twd,
                    })

                # 股數絕對上限
                max_shares = redlines.get('max_buy_shares', 1000)
                if quantity > max_shares:
                    return _fail('redline_shares_exceeded', {
                        'quantity': quantity,
                        'max_shares': max_shares,
                    })

                # AI 信心門檻
                ai_conf = order.get('ai_confidence')
                if ai_conf is not None:
                    threshold = redlines.get('ai_confidence_threshold', 0.7)
                    conf_val = (
                        {'high': 0.9, 'medium': 0.7, 'low': 0.5}.get(str(ai_conf).lower(), 0.0)
                        if isinstance(ai_conf, str)
                        else float(ai_conf)
                    )
                    if conf_val < threshold:
                        return _fail('low_ai_confidence', {
                            'confidence': conf_val,
                            'threshold': threshold,
                        })
    except Exception:
        pass  # safety redlines load failure is non-blocking

    # Compute investment score (non-blocking, appended to pass result)
    score_result = compute_investment_score(order, context)
    result = _pass()
    result['investment_score'] = score_result['investment_score']
    result['score_breakdown'] = score_result['score_breakdown']
    return result
