#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
MARKET_CACHE_PATH = STATE / 'market_cache.json'
WATCHLIST_PATH = STATE / 'watchlist.json'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
EVENT_CONTEXT_PATH = STATE / 'market_event_context.json'
OUTPUT_PATH = STATE / 'intraday_tape_context.json'

def safe_load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return default

def atomic_save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')

def classify_symbol_signal(symbol: str, quote: dict, group: str, market_context: dict, event_context: dict) -> dict:
    price = float(quote.get('current_price') or 0)
    open_p = float(quote.get('open') or 0)
    high_p = float(quote.get('high') or 0)
    low_p = float(quote.get('low') or 0)
    prev_p = float(quote.get('prev_close') or 0)

    # 1. Basic Availability Check
    if price <= 0:
        return {
            'symbol': symbol,
            'current_price': price,
            'intraday_position': 'unknown',
            'relative_strength': 'unknown',
            'tape_label': '資料不足',
            'rebound_watch': False,
            'falling_knife_risk': False,
        }

    # 2. Performance Metrics
    daily_return = (price - prev_p) / prev_p if prev_p > 0 else 0
    intraday_return = (price - open_p) / open_p if open_p > 0 else 0
    range_span = (high_p - low_p)
    range_pos = (price - low_p) / range_span if range_span > 0 else 0.5

    # 3. Logic Determination (Fact-Driven)
    tape_label = '區間震盪'
    relative_strength = 'neutral'
    rebound_watch = False
    falling_knife_risk = False
    
    # Thresholds (percentage)
    # Increased sensitivity for 0.5% moves
    if daily_return > 0.005:  # Up > 0.5%
        if intraday_return > 0.005:
            tape_label = '強勢噴發'
            relative_strength = 'very-strong'
        elif intraday_return < -0.005:
            tape_label = '高檔回吐'
            relative_strength = 'weakening'
        else:
            tape_label = '偏多震盪'
            relative_strength = 'strong'
    elif daily_return < -0.005: # Down > 0.5%
        if intraday_return < -0.005:
            tape_label = '破位下跌'
            relative_strength = 'very-weak'
            falling_knife_risk = True
        elif intraday_return > 0.005:
            tape_label = '跌深反彈'
            relative_strength = 'rebound'
            rebound_watch = True
        else:
            tape_label = '偏空震盪'
            relative_strength = 'weak'
    else:
        # Range Bound Logic
        if range_pos > 0.8:
            tape_label = '高檔盤整'
            relative_strength = 'firm'
        elif range_pos < 0.2:
            tape_label = '低檔支撐'
            relative_strength = 'soft'
        else:
            tape_label = '區間震盪'
            relative_strength = 'neutral'

    return {
        'symbol': symbol,
        'current_price': round(price, 4),
        'daily_return_pct': round(daily_return * 100, 2),
        'intraday_return_pct': round(intraday_return * 100, 2),
        'range_pos_pct': round(range_pos * 100, 1),
        'intraday_position': 'high' if range_pos > 0.8 else 'low' if range_pos < 0.2 else 'mid',
        'relative_strength': relative_strength,
        'tape_label': tape_label,
        'rebound_watch': rebound_watch,
        'falling_knife_risk': falling_knife_risk,
    }

def main() -> int:
    now = datetime.now(TW_TZ)
    market_cache_payload = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    market_cache = market_cache_payload.get('quotes', {})
    watchlist = safe_load_json(WATCHLIST_PATH, {'items': []})
    market_context = safe_load_json(MARKET_CONTEXT_PATH, {'market_regime': 'unknown'})
    event_context = safe_load_json(EVENT_CONTEXT_PATH, {'event_regime': 'unknown'})

    signals = []
    for item in watchlist.get('items', []):
        symbol = item.get('symbol')
        group = item.get('group') or item.get('category') or 'other'
        quote = market_cache.get(symbol) or {}
        signal = classify_symbol_signal(symbol, quote, group, market_context, event_context)
        signal['group'] = group
        signal['name'] = item.get('name', symbol)
        signals.append(signal)

    # Re-calculate Market Bias based on actual performance (FACT-DRIVEN)
    avg_daily_return = sum(s.get('daily_return_pct', 0) for s in signals) / len(signals) if signals else 0
    
    if avg_daily_return > 0.8:
        market_bias = 'bullish'
        summary = '多方控盤中；盤面強勁，多數標的呈現噴發態勢。'
    elif avg_daily_return < -0.8:
        market_bias = 'risk-off'
        summary = '空方佔優；盤面回撤明顯，需強化防禦布局。'
    elif any(s.get('rebound_watch') for s in signals):
        market_bias = 'rebound-watch'
        summary = '低檔反彈中；部分標的出現止跌訊號，靜待量能放大。'
    else:
        market_bias = 'neutral'
        summary = '區間震盪；多空陷入膠著，暫無明顯方向感。'

    payload = {
        'updated_at': now.isoformat(),
        'source': 'intraday-tape-context-v3-pro',
        'market_bias': market_bias,
        'tape_summary': summary,
        'watchlist_signals': signals,
    }
    atomic_save_json(OUTPUT_PATH, payload)
    print('INTRADAY_TAPE_CONTEXT_OK')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
