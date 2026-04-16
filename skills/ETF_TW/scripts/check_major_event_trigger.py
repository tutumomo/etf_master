#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
EXTERNAL_EVENT_CONTEXT_PATH = STATE / 'market_event_context.json'
EVENT_FLAG_PATH = STATE / 'major_event_flag.json'
EVENT_STATE_PATH = STATE / 'event_review_state.json'


def classify_level(anomalies: list[str], market_cache: dict, market_context: dict) -> tuple[str, str]:
    freshness_ts = market_cache.get('updated_at')
    risk_temperature = market_context.get('risk_temperature', 'normal')
    defensive_tilt = market_context.get('defensive_tilt', 'neutral')
    if not anomalies:
        return 'none', '無重大事件'
    if len(anomalies) >= 2:
        return 'L3', '多項異常同時觸發'
    if freshness_ts is None:
        return 'L2', '資料來源異常且缺少更新時間'
    if risk_temperature == 'elevated' or defensive_tilt == 'high':
        return 'L2', '台灣市場情勢偏保守，單一異常需提高警覺'
    return 'L1', '單一異常事件'


def event_hash(reason: str, level: str) -> str:
    return hashlib.sha1(f'{level}:{reason}'.encode('utf-8')).hexdigest()[:12]


def main() -> int:
    market_cache = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    market_context = safe_load_json(MARKET_CONTEXT_PATH, {'risk_temperature': 'normal', 'defensive_tilt': 'neutral'})
    external_event_context = safe_load_json(EXTERNAL_EVENT_CONTEXT_PATH, {'global_risk_level': 'unknown', 'geo_political_risk': 'unknown'})
    now = datetime.now(TW_TZ)
    anomalies = []
    for symbol, quote in market_cache.get('quotes', {}).items():
        price = float(quote.get('current_price') or 0)
        if price <= 0:
            anomalies.append(f'{symbol} 無有效報價')

    if external_event_context.get('global_risk_level') == 'elevated' or external_event_context.get('geo_political_risk') == 'high':
        market_context = {**market_context, 'risk_temperature': 'elevated', 'defensive_tilt': 'high'}
    level, category = classify_level(anomalies, market_cache, market_context)
    triggered = bool(anomalies)
    reason = '；'.join(anomalies) if anomalies else '無重大事件'
    current_hash = event_hash(reason, level)

    event_state = safe_load_json(EVENT_STATE_PATH, {
        'last_event_hash': None,
        'last_event_level': 'none',
        'last_triggered_at': None,
        'cooldown_minutes_default': 60,
        'merged_events_count': 0,
        'updated_at': None,
        'source': 'default',
    })

    should_notify = True
    merged_count = 0
    if triggered and event_state.get('last_event_hash') == current_hash:
        should_notify = False
        merged_count = int(event_state.get('merged_events_count') or 0) + 1
    elif triggered:
        merged_count = 1

    payload = {
        'triggered': triggered,
        'reason': reason,
        'level': level,
        'category': category,
        'event_hash': current_hash if triggered else None,
        'should_notify': should_notify if triggered else False,
        'merged_events_count': merged_count if triggered else 0,
        'checked_at': now.isoformat(),
        'source': 'check_major_event_trigger',
    }
    atomic_save_json(EVENT_FLAG_PATH, payload)

    event_state.update({
        'last_event_hash': current_hash if triggered else None,
        'last_event_level': level,
        'last_triggered_at': now.isoformat() if triggered else None,
        'merged_events_count': merged_count if triggered else 0,
        'updated_at': now.isoformat(),
        'source': 'check_major_event_trigger',
    })
    atomic_save_json(EVENT_STATE_PATH, event_state)
    print('MAJOR_EVENT_TRIGGER_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
