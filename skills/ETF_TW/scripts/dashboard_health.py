#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def build_health_summary_payload(*, market_event_context: dict, market_context_taiwan: dict, major_event_flag: dict,
                                 decision_quality: dict, auto_trade_state: dict, market_intelligence: dict,
                                 reconciliation_warnings: list[str], classify_freshness) -> dict[str, Any]:
    health_warnings = []
    for label, payload in [
        ('market_event_context', market_event_context),
        ('market_context_taiwan', market_context_taiwan),
        ('major_event_flag', major_event_flag),
        ('decision_quality', decision_quality),
        ('auto_trade_state', auto_trade_state),
        ('market_intelligence', market_intelligence),
    ]:
        if payload.get('_load_warning'):
            health_warnings.append(f"{label}: load failed")
        if payload.get('_schema_warning'):
            missing = ', '.join(payload['_schema_warning'].get('missing_keys', []))
            health_warnings.append(f"{label}: schema fallback ({missing})")

    stale_checks = [
        ('外部事件更新', market_event_context.get('updated_at')),
        ('台灣市場情勢更新', market_context_taiwan.get('updated_at')),
        ('事件檢查時間', major_event_flag.get('checked_at')),
        ('品質校正時間', decision_quality.get('evaluated_at')),
        ('最近掃描時間', auto_trade_state.get('last_scan_at')),
        ('技術指標更新', market_intelligence.get('updated_at')),
    ]
    stale_items = []
    for label, ts in stale_checks:
        freshness = classify_freshness(ts)
        if freshness['level'] in {'warn', 'bad'}:
            stale_items.append({'label': label, 'status': freshness['label'], 'ts': ts})

    intel_rows = market_intelligence.get('intelligence', {})
    intel_ready_count = sum(
        1 for row in intel_rows.values()
        if isinstance(row.get('history_30d'), list) and len(row.get('history_30d', [])) >= 20 and row.get('rsi') is not None
    )
    if not intel_rows and market_intelligence.get('updated_at'):
        health_warnings.append('market_intelligence: 無可用技術指標資料')
    elif intel_rows and intel_ready_count == 0:
        health_warnings.append('market_intelligence: 無可用技術指標資料')

    merged_warnings = health_warnings + list(reconciliation_warnings or [])

    return {
        'last_market_event_refresh': market_event_context.get('updated_at'),
        'last_taiwan_context_refresh': market_context_taiwan.get('updated_at'),
        'last_event_check': major_event_flag.get('checked_at'),
        'last_quality_scoring': decision_quality.get('evaluated_at'),
        'last_scan': auto_trade_state.get('last_scan_at'),
        'last_intelligence_refresh': market_intelligence.get('updated_at'),
        'intelligence_ready_count': intel_ready_count,
        'warnings': merged_warnings,
        'stale_items': stale_items,
        'health_summary': '正常' if not merged_warnings and not stale_items and all([
            market_event_context.get('updated_at'),
            market_context_taiwan.get('updated_at'),
            major_event_flag.get('checked_at'),
            decision_quality.get('evaluated_at'),
            market_intelligence.get('updated_at')
        ]) else '需注意'
    }
