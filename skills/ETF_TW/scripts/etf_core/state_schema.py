#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

REQUIRED_KEYS = {
    'market_event_context': ['event_regime', 'global_risk_level', 'summary'],
    'market_context_taiwan': ['market_regime', 'risk_temperature', 'context_summary'],
    'major_event_flag': ['triggered', 'reason', 'level'],
    'event_review_state': ['last_event_hash', 'last_event_level', 'merged_events_count'],
    'decision_quality': ['quality_summary', 'direction_score', 'risk_score'],
    'auto_trade_config': ['enabled', 'frequency_minutes', 'trading_hours_only'],
    'auto_trade_state': ['enabled', 'last_scan_at', 'last_decision_summary'],
    'auto_submit_state': ['enabled', 'live_submit_allowed', 'last_submit_at'],
    'auto_preview_candidate': ['symbol', 'side', 'mode'],
}


def validate_state_payload(kind: str, payload: Any, default: Any):
    if not isinstance(payload, dict):
        return default
    required = REQUIRED_KEYS.get(kind, [])
    missing = [key for key in required if key not in payload]
    if missing:
        if isinstance(default, dict):
            return {**default, '_schema_warning': {'kind': kind, 'missing_keys': missing, 'fallback_used': True}}
        return default
    return payload
