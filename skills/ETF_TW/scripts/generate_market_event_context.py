#!/usr/bin/env python3
"""Generate market event context from REAL data sources.

Previously this was entirely hardcoded (risk-off, elevated, high, etc).
Now it derives regime/risk from:
  1. Market intelligence (RSI, MACD, SMA, Bollinger Band signals)
  2. Shioaji snapshots (volume_ratio, change_rate, tick_type)
  3. Strategy overlay as sanity check

Future Phase B will add: news RSS, VIX, TWD/USD, FOMC calendar.
Future Phase C will add: LLM-based event interpretation.
"""
from __future__ import annotations

import json
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
OUTPUT_PATH = STATE / 'market_event_context.json'


def _compute_market_breadth(intel: dict) -> dict:
    """Analyze watchlist ETFs to determine market breadth signals.

    Returns:
        dict with keys: bullish_pct, bearish_pct, avg_rsi, avg_macd_hist,
        above_sma20_count, below_sma20_count, below_bb_mid_count
    """
    total = 0
    bullish = 0
    bearish = 0
    rsi_sum = 0.0
    macd_hist_sum = 0.0
    above_sma20 = 0
    below_sma20 = 0
    below_bb_mid = 0

    for sym, m in intel.items():
        price = m.get('last_price') or m.get('close', 0)
        if not price or price <= 0:
            continue

        total += 1
        rsi = m.get('rsi', 50)
        if isinstance(rsi, (int, float)):
            rsi_sum += rsi

        macd = m.get('macd', 0)
        macd_sig = m.get('macd_signal', 0)
        hist = (macd - macd_sig) if isinstance(macd, (int, float)) and isinstance(macd_sig, (int, float)) else 0
        macd_hist_sum += hist

        sma20 = m.get('sma20', 0)
        if isinstance(sma20, (int, float)) and isinstance(price, (int, float)):
            if price > sma20:
                above_sma20 += 1
            else:
                below_sma20 += 1

        bb_mid = m.get('bb_mid', 0)
        if isinstance(bb_mid, (int, float)) and isinstance(price, (int, float)):
            if price < bb_mid:
                below_bb_mid += 1

        # Count bullish (RSI 40-65, MACD bullish) vs bearish
        if isinstance(rsi, (int, float)) and 40 <= rsi <= 65 and hist > 0:
            bullish += 1
        elif isinstance(rsi, (int, float)) and (rsi > 75 or rsi < 30):
            bearish += 1
        elif hist < -0.1:
            bearish += 1

    if total == 0:
        return {
            'bullish_pct': 0, 'bearish_pct': 0,
            'avg_rsi': 50, 'avg_macd_hist': 0,
            'above_sma20_count': 0, 'below_sma20_count': 0,
            'below_bb_mid_count': 0, 'total': 0,
        }

    return {
        'bullish_pct': round(bullish / total * 100, 1),
        'bearish_pct': round(bearish / total * 100, 1),
        'avg_rsi': round(rsi_sum / total, 1),
        'avg_macd_hist': round(macd_hist_sum / total, 4),
        'above_sma20_count': above_sma20,
        'below_sma20_count': below_sma20,
        'below_bb_mid_count': below_bb_mid,
        'total': total,
    }


def _determine_regime(breadth: dict) -> tuple[str, str, str, str, str]:
    """Determine event regime from breadth data.

    Returns: (event_regime, global_risk_level, geo_political_risk, rate_risk, energy_risk)
    """
    bullish_pct = breadth['bullish_pct']
    bearish_pct = breadth['bearish_pct']
    avg_rsi = breadth['avg_rsi']
    above_sma20 = breadth['above_sma20_count']
    below_sma20 = breadth['below_sma20_count']

    # Decision matrix based on real signals
    if bearish_pct > 40:
        event_regime = 'risk-off'
        global_risk_level = 'elevated'
    elif bearish_pct > 20 or (above_sma20 > 0 and below_sma20 > above_sma20):
        event_regime = 'cautious'
        global_risk_level = 'moderate'
    elif bullish_pct > 50 and avg_rsi < 65:
        event_regime = 'risk-on'
        global_risk_level = 'normal'
    else:
        event_regime = 'neutral'
        global_risk_level = 'normal'

    # Geo-political and rate risks are inferred from defensive signals
    # In Phase B, these will come from real news/events
    # For now, derive from market behavior (defensive ETFs outperforming = geo risk)
    below_bb_mid_pct = breadth['below_bb_mid_count'] / max(breadth['total'], 1) * 100
    if below_bb_mid_pct > 30:
        geo_political_risk = 'medium'
        rate_risk = 'medium'
    else:
        geo_political_risk = 'low'
        rate_risk = 'low'

    energy_risk = 'medium'  # Default until Phase B adds real energy data

    # === Phase B: Macro/calendar risk overlay ===
    # Check if central bank meeting is imminent
    cal_data = safe_load_json(STATE / 'central_bank_calendar.json', {})
    next_major = cal_data.get('next_major')
    if next_major and next_major.get('days_until', 99) <= 7:
        # Pre-meeting period: elevate risk if not already high
        if global_risk_level == 'normal':
            global_risk_level = 'moderate'
            rate_risk = 'high'

    # Check VIX proxy
    macro = safe_load_json(STATE / 'macro_indicators.json', {})
    vix_proxy = macro.get('vix_proxy')
    if isinstance(vix_proxy, (int, float)) and vix_proxy > 25:
        if global_risk_level == 'normal':
            global_risk_level = 'moderate'
        if event_regime == 'neutral':
            event_regime = 'cautious'

    # Check news — support both old (news_headlines.json) and new (news_articles.json) formats
    news_data = safe_load_json(STATE / 'news_articles.json', {})
    if not news_data.get('articles'):
        news_data = safe_load_json(STATE / 'news_headlines.json', {})
        tag_counts = news_data.get('tag_counts', {})
    else:
        # Convert opencli format to tag_counts
        tag_counts = {}
        for a in news_data.get('articles', []):
            for cat in a.get('categories', []):
                tag_counts[cat] = tag_counts.get(cat, 0) + 1
    if tag_counts.get('geo_risk', 0) >= 3:
        geo_political_risk = 'high'
    elif tag_counts.get('geo_risk', 0) >= 1:
        if geo_political_risk == 'low':
            geo_political_risk = 'medium'

    # Check news rate_decision tags
    if tag_counts.get('rate_decision', 0) >= 2:
        rate_risk = 'high'
    elif tag_counts.get('rate_decision', 0) >= 1:
        if rate_risk == 'low':
            rate_risk = 'medium'

    return event_regime, global_risk_level, geo_political_risk, rate_risk, energy_risk


def _compute_defensive_bias(breadth: dict, event_regime: str) -> str:
    """Determine defensive bias from breadth + regime."""
    if event_regime == 'risk-off':
        return 'high'
    elif event_regime == 'cautious':
        return 'medium'
    elif event_regime == 'risk-on':
        return 'low'
    else:
        # Neutral: check if below_sma20 signals are present
        if breadth['below_sma20_count'] > breadth['above_sma20_count']:
            return 'medium'
        return 'low'


def _generate_summary(event_regime: str, global_risk: str, defensive_bias: str,
                      breadth: dict, active_events: list[str]) -> str:
    """Generate human-readable summary based on real signals."""
    parts = []

    regime_desc = {
        'risk-on': '市場偏多頭，多數 ETF 技術信號健康',
        'risk-off': '市場偏空頭，風險偏好明顯下降',
        'cautious': '市場氣氛偏謹慎，多空信號參半',
        'neutral': '市場氣氛中性，無明顯方向',
    }
    parts.append(regime_desc.get(event_regime, '市場氣氛不明'))

    # Add breadth detail
    if breadth['total'] > 0:
        parts.append(
            f"（{breadth['total']} 檔 ETF："
            f"多頭信號 {breadth['bullish_pct']}%，"
            f"空頭信號 {breadth['bearish_pct']}%，"
            f"均RSI {breadth['avg_rsi']}）"
        )

    if global_risk == 'elevated':
        parts.append('整體風險水準升高，建議提高防守權重。')
    elif global_risk == 'moderate':
        parts.append('風險中等，宜分批布局不宜追高。')

    if active_events:
        parts.append('關注事件：' + '、'.join(active_events))

    return ''.join(parts)


def _detect_active_events(breadth: dict, intel: dict) -> list[str]:
    """Detect active market events from technical signals + news + calendar."""
    events = []

    # Volume anomaly detection
    high_vol_syms = []
    low_vol_syms = []
    for sym, m in intel.items():
        price = m.get('last_price') or m.get('close', 0)
        if not price or price <= 0:
            continue
        rsi = m.get('rsi', 50)
        if isinstance(rsi, (int, float)):
            if rsi > 75:
                high_vol_syms.append(sym)
            elif rsi < 25:
                low_vol_syms.append(sym)

    if high_vol_syms:
        events.append(f"超買信號：{', '.join(high_vol_syms[:3])} RSI偏高，留意回檔風險")
    if low_vol_syms:
        events.append(f"超賣信號：{', '.join(low_vol_syms[:3])} RSI偏低，可能具反彈機會")

    # MACD divergence detection
    macd_div_syms = []
    for sym, m in intel.items():
        price = m.get('last_price') or m.get('close', 0)
        if price <= 0:
            continue
        macd = m.get('macd', 0)
        macd_sig = m.get('macd_signal', 0)
        hist = (macd - macd_sig) if isinstance(macd, (int, float)) and isinstance(macd_sig, (int, float)) else 0
        sma20 = m.get('sma20', 0)
        if isinstance(sma20, (int, float)) and price > sma20 and hist < -0.05:
            macd_div_syms.append(sym)

    if macd_div_syms:
        events.append(f"MACD 背離：{', '.join(macd_div_syms[:3])} 價格均線上方但動能減弱")

    # Broad market regime note
    if breadth['below_sma20_count'] > breadth['above_sma20_count']:
        events.append('多數標的位於20日均線下方，短線偏弱')

    # === Phase B: News headlines (support both formats) ===
    news_articles_data = safe_load_json(STATE / 'news_articles.json', {})
    if news_articles_data.get('articles'):
        # New opencli format
        headlines = news_articles_data.get('articles', [])
        tag_counts = {}
        for a in headlines:
            for cat in a.get('categories', []):
                tag_counts[cat] = tag_counts.get(cat, 0) + 1
        sentiment_counts = {
            'bearish': news_articles_data.get('negative_sentiment', 0),
            'bullish': 0,  # opencli format doesn't have bullish count
        }
    else:
        # Old RSS format
        news_data = safe_load_json(STATE / 'news_headlines.json', {})
        headlines = news_data.get('headlines', [])
        tag_counts = news_data.get('tag_counts', {})
        sentiment_counts = news_data.get('sentiment_counts', {})

    # Add tagged news events
    if tag_counts.get('rate_decision', 0) > 0:
        events.append(f'新聞標籤：利率決策相關 {tag_counts["rate_decision"]} 則')
    if tag_counts.get('geo_risk', 0) > 0:
        events.append(f'新聞標籤：地緣風險相關 {tag_counts["geo_risk"]} 則')
    if tag_counts.get('etf_related', 0) > 0:
        events.append(f'新聞標籤：ETF相關 {tag_counts["etf_related"]} 則')

    # News sentiment summary
    bear_count = sentiment_counts.get('bearish', 0)
    bull_count = sentiment_counts.get('bullish', 0)
    if bear_count > bull_count + 2:
        events.append(f'新聞情緒偏空（空{bear_count} vs 多{bull_count}）')
    elif bull_count > bear_count + 2:
        events.append(f'新聞情緒偏多（多{bull_count} vs 空{bear_count}）')

    # Individual headline events (top tagged)
    tagged_headlines = [h for h in headlines if h.get('tags')][:3]
    for h in tagged_headlines:
        events.append(f"關注：{h['title'][:40]}… [{','.join(h['tags'][:2])}]")

    # === Phase B: Central bank calendar ===
    cal_data = safe_load_json(STATE / 'central_bank_calendar.json', {})
    next_major = cal_data.get('next_major')
    if next_major and next_major.get('days_until', 99) <= 14:
        events.append(f"近期央行會議：{next_major['event']}（{next_major['days_until']}天後）")
        # If FOMC/CBC within 7 days, elevate rate_risk
        if next_major.get('days_until', 99) <= 7:
            events.append('央行會議一週內，利率風險升高')

    # === Phase B: Macro indicators ===
    macro = safe_load_json(STATE / 'macro_indicators.json', {})
    vix = macro.get('vix_proxy')
    trend = macro.get('taiex_trend')
    m_breadth = macro.get('market_breadth', {})

    if isinstance(vix, (int, float)) and vix > 20:
        events.append(f'波動代理指標偏高（VIX proxy {vix}），市場不安情緒升溫')
    if trend == 'down':
        events.append('加權指數趨勢偏空（ETF 動能代理推算）')

    return events


def main() -> int:
    now = datetime.now(TW_TZ)

    # Load market intelligence (real RSI/MACD/BB data)
    intel_data = safe_load_json(STATE / 'market_intelligence.json', {'intelligence': {}})
    intel = intel_data.get('intelligence', {})

    if not intel:
        # Fallback: no intelligence data available
        payload = {
            'event_regime': 'unknown',
            'global_risk_level': 'unknown',
            'geo_political_risk': 'unknown',
            'rate_risk': 'unknown',
            'energy_risk': 'unknown',
            'taiwan_equity_impact': 'unknown',
            'defensive_bias': 'neutral',
            'summary': '缺乏市場技術情報，無法判斷事件層情境，建議暫緩動作。',
            'active_events': ['市場技術情報不足'],
            'breadth': {},
            'updated_at': now.isoformat(),
            'source': 'event-context-derived-v2-empty',
        }
        atomic_save_json(OUTPUT_PATH, payload)
        print('MARKET_EVENT_CONTEXT_OK_NO_DATA')
        return 0

    # Compute real breadth signals
    breadth = _compute_market_breadth(intel)

    # Detect events from signals
    active_events = _detect_active_events(breadth, intel)

    # Determine regime from breadth
    event_regime, global_risk, geo_risk, rate_risk, energy_risk = _determine_regime(breadth)

    # Determine defensive bias
    defensive_bias = _compute_defensive_bias(breadth, event_regime)

    # Determine equity impact
    impact_map = {
        'risk-off': 'cautious',
        'cautious': 'cautious',
        'risk-on': 'positive',
        'neutral': 'neutral',
    }
    taiwan_equity_impact = impact_map.get(event_regime, 'neutral')

    # Generate summary
    summary = _generate_summary(event_regime, global_risk, defensive_bias, breadth, active_events)

    payload = {
        'event_regime': event_regime,
        'global_risk_level': global_risk,
        'geo_political_risk': geo_risk,
        'rate_risk': rate_risk,
        'energy_risk': energy_risk,
        'taiwan_equity_impact': taiwan_equity_impact,
        'defensive_bias': defensive_bias,
        'summary': summary,
        'active_events': active_events,
        'breadth': breadth,
        'updated_at': now.isoformat(),
        'source': 'event-context-derived-v2',
    }
    atomic_save_json(OUTPUT_PATH, payload)
    print('MARKET_EVENT_CONTEXT_OK')
    print(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())