#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, safe_load_jsonl, atomic_save_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
DECISION_LOG_PATH = STATE / 'decision_log.jsonl'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
STRATEGY_LINK_PATH = STATE / 'strategy_link.json'
REGIME_BUCKET_STATS_PATH = STATE / 'regime_bucket_stats.json'


def main() -> int:
    now = datetime.now(TW_TZ)
    logs = safe_load_jsonl(DECISION_LOG_PATH)
    market_context = safe_load_json(MARKET_CONTEXT_PATH, {'market_regime': 'unknown', 'risk_temperature': 'unknown'})
    strategy = safe_load_json(STRATEGY_LINK_PATH, {'base_strategy': '未知', 'scenario_overlay': '未知'})

    base_strat = strategy.get('base_strategy')
    overlay = strategy.get('scenario_overlay')
    regime = market_context.get('market_regime')
    risk_temp = market_context.get('risk_temperature')

    # Filter logs that match the current strategy and regime bucket
    bucket_logs = []
    for row in logs:
        row_strat = row.get('strategy', {})
        row_market = row.get('market_context', {})
        
        if (row_strat.get('base_strategy') == base_strat and 
            row_strat.get('scenario_overlay') == overlay and
            row_market.get('market_regime') == regime and
            row_market.get('risk_temperature') == risk_temp):
            bucket_logs.append(row)

    action_counter = Counter(row.get('action', 'unknown') for row in bucket_logs)
    bucket_key = f"{base_strat}|{overlay}|{regime}|{risk_temp}"

    payload = {
        'updated_at': now.isoformat(),
        'source': 'build_regime_bucket_stats',
        'bucket_key': bucket_key,
        'strategy': strategy,
        'market_regime': regime,
        'risk_temperature': risk_temp,
        'decision_count': len(bucket_logs),
        'total_logs_scanned': len(logs),
        'action_breakdown': dict(action_counter),
        'summary': (
            f"bucket={bucket_key}；count={len(bucket_logs)}；"
            f"actions={dict(action_counter)}"
        ),
    }
    atomic_save_json(REGIME_BUCKET_STATS_PATH, payload)
    print('REGIME_BUCKET_STATS_OK')
    print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
