#!/usr/bin/env python3
"""
sync_macro_indicators.py — 抓取宏觀指標寫入 state/macro_indicators.json

資料來源：
1. shioaji API: TAIEX 加權指數、成交值、漲跌幅
2. Fallback: market_intelligence 推算（無 shioaji 時）

寫入欄位：
- taiex: {price, change, change_pct, volume, high, low, updated_at}
- taiex_trend: up/down/flat（5日趨勢）
- twd_usd: 匯率（shioaji 或待補）
- vix_proxy: 波動率代理（從 market_intelligence 年化波動推算）
- market_breadth: 漲跌家數比（從 watchlist 報價推算）

此腳本由 sync 觸發或手動執行。
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from etf_core.state_io import safe_load_json, atomic_save_json
from etf_core.state_schema import validate_state_payload
from etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')

MACRO_PATH = STATE / 'macro_indicators.json'
MARKET_INTEL_PATH = STATE / 'market_intelligence.json'
MARKET_CACHE_PATH = STATE / 'market_cache.json'
WATCHLIST_PATH = STATE / 'watchlist.json'


def _try_shioaji_taiex() -> dict | None:
    """Try to get TAIEX data via shioaji."""
    try:
        import shioaji as sj
        api = sj.Shioaji(simulation=True)
        # Login with env or empty (simulation mode)
        import os
        person_id = os.environ.get('SHIOAJI_PERSON_ID', '')
        passwd = os.environ.get('SHIOAJI_PASSWD', '')
        if not person_id or not passwd:
            api.login(person_id, passwd)
        else:
            api.login(person_id, passwd)

        # TAIEX index contract
        contract = api.Contracts.Indexs.TSE_TAIEX
        if not contract:
            return None

        # Get snapshot
        snapshot = api.snapshots([contract])
        if not snapshot:
            return None

        s = snapshot[0]
        api.logout()
        return {
            'price': float(s.close),
            'change': float(s.change),
            'change_pct': float(s.change_rate) * 100,  # shioaji gives decimal
            'volume': int(s.total_volume) if hasattr(s, 'total_volume') else 0,
            'high': float(s.high) if hasattr(s, 'high') else 0,
            'low': float(s.low) if hasattr(s, 'low') else 0,
        }
    except Exception as e:
        print(f"  [macro] shioaji TAIEX failed: {e}")
        return None


def _estimate_taiex_trend(intel: dict) -> str:
    """Estimate TAIEX trend from ETF intelligence (proxy)."""
    # Use average momentum_20d across all ETFs as proxy
    momentums = []
    for sym, m in intel.items():
        mom = m.get('momentum_20d')
        if isinstance(mom, (int, float)):
            momentums.append(mom)

    if not momentums:
        return 'unknown'

    avg_mom = sum(momentums) / len(momentums)
    if avg_mom > 3:
        return 'up'
    elif avg_mom < -3:
        return 'down'
    else:
        return 'flat'


def _estimate_vix_proxy(intel: dict) -> float | None:
    """Estimate VIX proxy from annualized volatility of ETF prices."""
    # Use average BB width as volatility proxy
    bb_widths = []
    for sym, m in intel.items():
        bb_upper = m.get('bb_upper', 0)
        bb_lower = m.get('bb_lower', 0)
        bb_mid = m.get('bb_mid', 0)
        if all(isinstance(x, (int, float)) and x > 0 for x in [bb_upper, bb_lower, bb_mid]):
            width_pct = (bb_upper - bb_lower) / bb_mid * 100
            bb_widths.append(width_pct)

    if not bb_widths:
        return None

    avg_width = sum(bb_widths) / len(bb_widths)
    # rough proxy: BB width ~ 2*sigma*2 = 4*sigma, vix ~ sigma_annual
    # This is very rough but gives directional signal
    vix_proxy = round(avg_width * 1.5, 1)  # empirical scaling
    return vix_proxy


def _estimate_market_breadth(market_cache: dict, watchlist: dict) -> dict:
    """Estimate market breadth from watchlist quote changes."""
    quotes = market_cache.get('quotes', {})
    items = watchlist.get('items', [])
    up = 0
    down = 0
    unchanged = 0
    total = 0

    for item in items:
        sym = item.get('symbol', '')
        q = quotes.get(sym, {})
        change_pct = q.get('change_pct') or q.get('change_rate')
        if isinstance(change_pct, (int, float)):
            total += 1
            if change_pct > 0.1:
                up += 1
            elif change_pct < -0.1:
                down += 1
            else:
                unchanged += 1

    if total == 0:
        return {'up': 0, 'down': 0, 'unchanged': 0, 'ratio': 'unknown', 'breadth': 'unknown'}

    ratio = up / max(down, 1)
    if ratio > 2:
        breadth = 'strong_bull'
    elif ratio > 1.2:
        breadth = 'bull'
    elif ratio > 0.8:
        breadth = 'neutral'
    elif ratio > 0.5:
        breadth = 'bear'
    else:
        breadth = 'strong_bear'

    return {
        'up': up,
        'down': down,
        'unchanged': unchanged,
        'ratio': round(ratio, 2),
        'breadth': breadth,
    }


def sync_macro_indicators() -> dict:
    """Main sync function. Returns the written payload."""
    now = datetime.now(TW_TZ)
    intel_data = safe_load_json(MARKET_INTEL_PATH, {'intelligence': {}})
    intel = intel_data.get('intelligence', {})
    market_cache = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    watchlist = safe_load_json(WATCHLIST_PATH, {'items': []})

    # 1. TAIEX
    taiex = _try_shioaji_taiex()
    if not taiex:
        # Fallback: estimate from ETF data
        prices = [m.get('last_price', 0) for m in intel.values() if isinstance(m.get('last_price'), (int, float)) and m.get('last_price', 0) > 0]
        taiex = {
            'price': None,
            'change': None,
            'change_pct': None,
            'volume': None,
            'high': None,
            'low': None,
            'note': 'shioaji unavailable, using ETF proxy',
        }

    # 2. Trend
    taiex_trend = _estimate_taiex_trend(intel)

    # 3. VIX proxy
    vix_proxy = _estimate_vix_proxy(intel)

    # 4. Market breadth
    breadth = _estimate_market_breadth(market_cache, watchlist)

    # 5. TWD/USD — shioaji doesn't provide this easily, mark as TODO
    twd_usd = None

    payload = {
        'taiex': taiex,
        'taiex_trend': taiex_trend,
        'vix_proxy': vix_proxy,
        'twd_usd': twd_usd,
        'market_breadth': breadth,
        'updated_at': now.isoformat(),
        'source': 'sync_macro_indicators',
    }

    # Validate & write
    validated = validate_state_payload('macro_indicators', payload, {
        'taiex_trend': 'unknown', 'market_breadth': {'breadth': 'unknown'}
    })
    atomic_save_json(MACRO_PATH, validated)
    print(f"MACRO_INDICATORS_OK: trend={taiex_trend}, breadth={breadth.get('breadth', '?')}, vix_proxy={vix_proxy}")
    return validated


if __name__ == '__main__':
    sync_macro_indicators()