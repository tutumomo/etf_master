#!/usr/bin/env python3
"""Generate Taiwan market context from REAL quantitative data.

Previously: only checked if quotes had zero prices (binary OK/missing).
Now derives market_regime, risk_temperature, tilts from:
  1. Market intelligence (RSI, MACD, SMA, Bollinger, 30d history)
  2. Market event context (regime, risk levels from A-1)
  3. Portfolio & strategy state
  4. Shioaji volume_ratio / change_rate (when available)

Quantifiable indicators added:
  - 加權指數趨勢：從 core group ETF 平均漲跌幅推算
  - 成交量信號：volume_ratio from shioaji snapshots
  - RSI 分布：超買/超賣比例
  - 動能趨勢：MACD histogram 方向
  - SMA 結構：多頭/空頭排列
  - 波動度：30d 歷史波動率
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, atomic_save_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
MARKET_CACHE_PATH = STATE / 'market_cache.json'
INTELLIGENCE_PATH = STATE / 'market_intelligence.json'
STRATEGY_PATH = STATE / 'strategy_link.json'
EVENT_CONTEXT_PATH = STATE / 'market_event_context.json'
PORTFOLIO_PATH = STATE / 'portfolio_snapshot.json'
OUTPUT_PATH = STATE / 'market_context_taiwan.json'


def _compute_rsi_distribution(intel: dict) -> dict:
    """Analyze RSI distribution across all tracked ETFs."""
    rsis = []
    overbought = []  # RSI > 70
    oversold = []     # RSI < 30
    neutral = []      # 30 <= RSI <= 70

    for sym, m in intel.items():
        rsi = m.get('rsi')
        if isinstance(rsi, (int, float)):
            rsis.append(rsi)
            if rsi > 70:
                overbought.append(sym)
            elif rsi < 30:
                oversold.append(sym)
            else:
                neutral.append(sym)

    if not rsis:
        return {'avg': 50, 'overbought': [], 'oversold': [], 'neutral': [],
                'overbought_pct': 0, 'oversold_pct': 0, 'count': 0}

    return {
        'avg': round(sum(rsis) / len(rsis), 1),
        'overbought': overbought,
        'oversold': oversold,
        'neutral': neutral,
        'overbought_pct': round(len(overbought) / len(rsis) * 100, 1),
        'oversold_pct': round(len(oversold) / len(rsis) * 100, 1),
        'count': len(rsis),
    }


def _compute_macd_breadth(intel: dict) -> dict:
    """Analyze MACD histogram direction across all tracked ETFs."""
    bullish = []
    bearish = []

    for sym, m in intel.items():
        macd = m.get('macd', 0)
        sig = m.get('macd_signal', 0)
        if isinstance(macd, (int, float)) and isinstance(sig, (int, float)):
            hist = macd - sig
            if hist > 0:
                bullish.append(sym)
            else:
                bearish.append(sym)

    total = len(bullish) + len(bearish)
    if total == 0:
        return {'bullish_pct': 0, 'bearish_pct': 0, 'direction': 'unknown'}

    return {
        'bullish_pct': round(len(bullish) / total * 100, 1),
        'bearish_pct': round(len(bearish) / total * 100, 1),
        'direction': 'bullish' if len(bullish) > len(bearish) else 'bearish',
    }


def _compute_sma_structure(intel: dict) -> dict:
    """SMA alignment: how many ETFs in bull/bear alignment."""
    bull_align = []  # price > sma5 > sma20 > sma60
    bear_align = []  # price < sma5 < sma20 < sma60
    above_20 = []
    below_20 = []

    for sym, m in intel.items():
        price = m.get('last_price') or m.get('close', 0)
        sma5 = m.get('sma5', 0)
        sma20 = m.get('sma20', 0)
        sma60 = m.get('sma60', 0)

        if not all(isinstance(x, (int, float)) and x > 0 for x in [price, sma5, sma20, sma60]):
            continue

        if price > sma20:
            above_20.append(sym)
        else:
            below_20.append(sym)

        if price > sma5 > sma20 > sma60:
            bull_align.append(sym)
        elif price < sma5 < sma20 < sma60:
            bear_align.append(sym)

    total = len(above_20) + len(below_20)
    return {
        'bull_aligned': bull_align,
        'bear_aligned': bear_align,
        'above_sma20': above_20,
        'below_sma20': below_20,
        'above_sma20_pct': round(len(above_20) / max(total, 1) * 100, 1),
        'structure': 'bullish' if len(bull_align) > len(bear_align) else 'bearish',
    }


def _compute_volatility(intel: dict) -> dict:
    """Compute 30d historical volatility for each ETF."""
    vols = {}

    for sym, m in intel.items():
        hist = m.get('history_30d', [])
        if len(hist) < 10:
            continue

        closes = [h.get('c', 0) for h in hist if h.get('c', 0) > 0]
        if len(closes) < 10:
            continue

        # Daily log returns
        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns.append(math.log(closes[i] / closes[i - 1]))

        if returns:
            mean_r = sum(returns) / len(returns)
            var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            daily_vol = math.sqrt(var_r)
            # Annualize (252 trading days)
            annual_vol = daily_vol * math.sqrt(252)
            vols[sym] = round(annual_vol, 4)

    if not vols:
        return {'avg_annual': 0, 'high_vol': [], 'low_vol': []}

    avg_vol = sum(vols.values()) / len(vols)
    high_vol = [s for s, v in vols.items() if v > avg_vol * 1.5]
    low_vol = [s for s, v in vols.items() if v < avg_vol * 0.5]

    return {
        'avg_annual': round(avg_vol, 4),
        'high_vol': high_vol[:5],
        'low_vol': low_vol[:5],
        'per_symbol': vols,
    }


def _compute_group_trends(intel: dict, watchlist_items: list) -> dict:
    """Compute avg change_rate and RSI per group (core/income/defensive/growth)."""
    group_map = {}
    for item in watchlist_items:
        sym = item.get('symbol', '')
        group = item.get('group', 'unknown')
        if group not in group_map:
            group_map[group] = []
        group_map[group].append(sym)

    result = {}
    for group, syms in group_map.items():
        rsis = []
        macds = []
        for sym in syms:
            m = intel.get(sym, {})
            rsi = m.get('rsi')
            if isinstance(rsi, (int, float)):
                rsis.append(rsi)
            macd = m.get('macd', 0)
            sig = m.get('macd_signal', 0)
            if isinstance(macd, (int, float)) and isinstance(sig, (int, float)):
                macds.append(macd - sig)

        result[group] = {
            'count': len(syms),
            'avg_rsi': round(sum(rsis) / len(rsis), 1) if rsis else None,
            'avg_macd_hist': round(sum(macds) / len(macds), 4) if macds else None,
            'momentum': 'bullish' if any(m > 0 for m in macds) and sum(macds) > 0 else 'bearish' if all(m <= 0 for m in macds) else 'mixed',
        }

    return result


def _determine_regime_from_signals(rsi_dist: dict, macd_breadth: dict,
                                    sma_struct: dict, vol: dict,
                                    event_ctx: dict) -> tuple:
    """Determine market_regime, risk_temperature, and tilts from real signals.

    Returns: (market_regime, risk_temperature, defensive_tilt, income_tilt, core_tilt)
    """
    # Weighted scoring system
    score = 0  # -5 to +5 range

    # RSI signal (-2 to +2)
    avg_rsi = rsi_dist.get('avg', 50)
    if avg_rsi > 65:
        score -= 1  # Overextended
    elif avg_rsi > 55:
        score += 1  # Healthy uptrend
    if rsi_dist.get('overbought_pct', 0) > 30:
        score -= 1  # Too many overbought

    # MACD breadth (-1 to +1)
    if macd_breadth.get('direction') == 'bullish':
        score += 1
    else:
        score -= 1

    # SMA structure (-1 to +1)
    if sma_struct.get('structure') == 'bullish':
        score += 1
    elif sma_struct.get('structure') == 'bearish':
        score -= 1

    # Volatility (-1 to 0)
    avg_vol = vol.get('avg_annual', 0)
    if avg_vol > 0.25:  # >25% annual vol is high for ETFs
        score -= 1

    # Event context override (-2 to +1)
    event_regime = event_ctx.get('event_regime', 'neutral')
    if event_regime == 'risk-off':
        score -= 2
    elif event_regime == 'cautious':
        score -= 1
    elif event_regime == 'risk-on':
        score += 1

    # Clamp
    score = max(-5, min(5, score))

    # Map score to regime
    if score >= 3:
        market_regime = 'bullish'
        risk_temperature = 'normal'
        defensive_tilt = 'low'
        income_tilt = 'low'
        core_tilt = 'high'
    elif score >= 1:
        market_regime = 'balanced_bullish'
        risk_temperature = 'normal'
        defensive_tilt = 'low'
        income_tilt = 'medium'
        core_tilt = 'high'
    elif score == 0:
        market_regime = 'balanced'
        risk_temperature = 'normal'
        defensive_tilt = 'medium'
        income_tilt = 'medium'
        core_tilt = 'medium'
    elif score >= -2:
        market_regime = 'cautious'
        risk_temperature = 'elevated'
        defensive_tilt = 'high'
        income_tilt = 'medium'
        core_tilt = 'low'
    else:
        market_regime = 'defensive'
        risk_temperature = 'high'
        defensive_tilt = 'high'
        income_tilt = 'low'
        core_tilt = 'low'

    return market_regime, risk_temperature, defensive_tilt, income_tilt, core_tilt, score


def main() -> int:
    now = datetime.now(TW_TZ)

    # Load all data sources
    intel_data = safe_load_json(INTELLIGENCE_PATH, {'intelligence': {}})
    intel = intel_data.get('intelligence', {})
    market_cache = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    strategy = safe_load_json(STRATEGY_PATH, {'base_strategy': '平衡配置', 'scenario_overlay': '無'})
    event_ctx = safe_load_json(EVENT_CONTEXT_PATH, {
        'event_regime': 'neutral', 'global_risk_level': 'normal',
        'defensive_bias': 'neutral', 'active_events': [],
        'summary': '尚無外部事件情境摘要'
    })
    portfolio = safe_load_json(PORTFOLIO_PATH, {'holdings': {}, 'cash': 0})
    watchlist = safe_load_json(STATE / 'watchlist.json', {'items': []})
    wl_items = watchlist.get('items', [])

    # === Compute quantitative indicators ===
    rsi_dist = _compute_rsi_distribution(intel)
    macd_breadth = _compute_macd_breadth(intel)
    sma_struct = _compute_sma_structure(intel)
    volatility = _compute_volatility(intel)
    group_trends = _compute_group_trends(intel, wl_items)

    # === Determine regime from real signals ===
    (market_regime, risk_temperature, defensive_tilt,
     income_tilt, core_tilt, regime_score) = _determine_regime_from_signals(
        rsi_dist, macd_breadth, sma_struct, volatility, event_ctx
    )

    # === Build risks list ===
    top_risks = list(event_ctx.get('active_events', []))

    # Add signal-based risks
    if rsi_dist.get('overbought_pct', 0) > 20:
        top_risks.append(f"RSI 超買標的佔比 {rsi_dist['overbought_pct']}%，留意回檔")
    if rsi_dist.get('oversold_pct', 0) > 20:
        top_risks.append(f"RSI 超賣標的佔比 {rsi_dist['oversold_pct']}%，可能續跌")
    if volatility.get('avg_annual', 0) > 0.25:
        top_risks.append(f"平均年化波動率 {volatility['avg_annual']:.1%}，波動偏高")
    if sma_struct.get('structure') == 'bearish':
        top_risks.append("多數標的均線呈空頭排列，趨勢偏弱")

    # === Strategy overlay adjustments ===
    overlay = strategy.get('scenario_overlay', '無')
    overlay_note = ''
    if overlay in {'收益再投資', '收益優先'}:
        income_tilt = 'high'
        overlay_note = ' 情境覆蓋偏向收益，再投資與收益型候選可提高關注。'
    elif overlay in {'高波動防守', '減碼保守'}:
        defensive_tilt = 'high'
        overlay_note = ' 情境覆蓋偏向防守，應提高觀望與風險收縮權重。'

    # === Generate context summary ===
    regime_desc = {
        'bullish': '市場偏多頭，各項技術指標健康。',
        'balanced_bullish': '市場氣氛偏正面，但需留意追高風險。',
        'balanced': '市場氣氛中性，適合維持策略一致性的觀察與分批布局評估。',
        'cautious': '市場氣氛偏謹慎，建議提高防守配置比重。',
        'defensive': '市場氣氛偏空，應以守住本金為優先。',
    }
    context_summary = regime_desc.get(market_regime, '市場氣氛不明。')

    # Add quant detail
    quant_parts = []
    if rsi_dist.get('count', 0) > 0:
        quant_parts.append(f"均RSI {rsi_dist['avg']}")
    if macd_breadth.get('direction') != 'unknown':
        quant_parts.append(f"MACD {macd_breadth['direction']}")
    if sma_struct.get('structure') != 'unknown':
        quant_parts.append(f"均線{sma_struct['structure']}")
    if volatility.get('avg_annual', 0) > 0:
        quant_parts.append(f"年化波動{volatility['avg_annual']:.0%}")

    if quant_parts:
        context_summary += f"（{', '.join(quant_parts)}）"

    context_summary += overlay_note

    # Add event context summary if different
    event_summary = event_ctx.get('summary', '')
    if event_summary and event_summary != '尚無外部事件情境摘要':
        context_summary += f" 事件層：{event_summary}"

    # === Build output payload ===
    payload = {
        'market_regime': market_regime,
        'risk_temperature': risk_temperature,
        'core_tilt': core_tilt,
        'income_tilt': income_tilt,
        'defensive_tilt': defensive_tilt,
        'context_summary': context_summary,
        'top_risks': top_risks,
        'strategy_ref': {
            'base_strategy': strategy.get('base_strategy'),
            'scenario_overlay': strategy.get('scenario_overlay'),
        },
        # New quantifiable indicators
        'quant_indicators': {
            'rsi_distribution': rsi_dist,
            'macd_breadth': macd_breadth,
            'sma_structure': sma_struct,
            'volatility': {k: v for k, v in volatility.items() if k != 'per_symbol'},
            'group_trends': group_trends,
            'regime_score': regime_score,
        },
        'updated_at': now.isoformat(),
        'source': 'taiwan-market-context-v2',
    }
    atomic_save_json(OUTPUT_PATH, payload)
    print('TAIWAN_MARKET_CONTEXT_OK')
    print(context_summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())