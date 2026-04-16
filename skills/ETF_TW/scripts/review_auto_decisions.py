#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, safe_append_jsonl, safe_load_jsonl
from etf_core.state_schema import validate_state_payload

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
DECISION_LOG_PATH = STATE / 'decision_log.jsonl'
REVIEW_LOG_PATH = STATE / 'decision_review.jsonl'
DECISION_OUTCOMES_PATH = STATE / 'decision_outcomes.jsonl'
DECISION_OUTCOME_SUMMARY_PATH = STATE / 'decision_outcome_summary.json'
CONTEXT_WEIGHTS_PATH = STATE / 'context_weights.json'
DECISION_EXPERIMENTS_PATH = STATE / 'decision_experiments.json'
MAJOR_EVENT_FLAG_PATH = STATE / 'major_event_flag.json'
QUALITY_PATH = STATE / 'decision_quality.json'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
INTRADAY_TAPE_CONTEXT_PATH = STATE / 'intraday_tape_context.json'
STRATEGY_LINK_PATH = STATE / 'strategy_link.json'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['daily', 'weekly'], required=True)
    args = parser.parse_args()

    now = datetime.now(TW_TZ)
    logs = safe_load_jsonl(DECISION_LOG_PATH)
    horizon = timedelta(days=1 if args.mode == 'daily' else 7)
    recent = []
    for row in logs:
        ts = datetime.fromisoformat(row['scanned_at'])
        if now - ts <= horizon:
            recent.append(row)

    major_event = validate_state_payload('major_event_flag', safe_load_json(MAJOR_EVENT_FLAG_PATH, {'triggered': False, 'reason': '無', 'level': 'none'}), {'triggered': False, 'reason': '無', 'level': 'none'})
    quality = validate_state_payload('decision_quality', safe_load_json(QUALITY_PATH, {'quality_summary': '尚無品質校正摘要', 'direction_score': 0, 'risk_score': 0}), {'quality_summary': '尚無品質校正摘要', 'direction_score': 0, 'risk_score': 0})
    market_context = validate_state_payload('market_context_taiwan', safe_load_json(MARKET_CONTEXT_PATH, {'context_summary': '尚無台灣市場情勢摘要', 'risk_temperature': 'normal', 'market_regime': 'unknown'}), {'market_regime': 'unknown', 'risk_temperature': 'normal', 'context_summary': '尚無台灣市場情勢摘要'})
    tape_context = safe_load_json(INTRADAY_TAPE_CONTEXT_PATH, {'market_bias': 'unknown', 'tape_summary': '尚無盤感摘要', 'watchlist_signals': []})
    outcomes = safe_load_jsonl(DECISION_OUTCOMES_PATH)
    outcome_summary = safe_load_json(DECISION_OUTCOME_SUMMARY_PATH, {'observed': 0, 'insufficient_data': 0, 'pending': 0})
    context_weights = safe_load_json(CONTEXT_WEIGHTS_PATH, {'weights': {}})
    experiments = safe_load_json(DECISION_EXPERIMENTS_PATH, {'experiments': []})
    strategy = safe_load_json(STRATEGY_LINK_PATH, {'base_strategy': '未知', 'scenario_overlay': '未知'})

    if recent:
        latest = recent[-1]
        summary = f"{args.mode} 檢討：最近 {len(recent)} 次決策，以 {latest['action']} 為最新動作。"
        if latest.get('uncertainty'):
            summary += f" 不確定性評估：{latest['uncertainty']}。"
        if latest.get('anomalies'):
            summary += ' 異常紀錄：' + '；'.join(latest['anomalies'])
    else:
        summary = f"{args.mode} 檢討：期間內沒有決策紀錄。"

    if major_event.get('triggered'):
        summary += f" 重大事件旗標：{major_event.get('reason')}。"
    if quality.get('quality_summary'):
        summary += f" 品質校正：{quality.get('quality_summary')}"
    if market_context.get('context_summary'):
        summary += f" 台灣市場情境：{market_context.get('context_summary')}"

    pending_outcomes = outcome_summary.get('pending', 0)
    observed_outcomes = outcome_summary.get('observed', 0)
    insufficient_outcomes = outcome_summary.get('insufficient_data', 0)
    active_experiments = sum(1 for row in experiments.get('experiments', []) if row.get('status') == 'active')

    regime_summary = (
        f"Regime review：策略 {strategy.get('base_strategy')} / {strategy.get('scenario_overlay')}；"
        f"market_regime={market_context.get('market_regime')}；"
        f"risk_temperature={market_context.get('risk_temperature')}。"
    )
    if market_context.get('income_tilt') == 'high':
        regime_summary += ' 收益型候選權重偏高。'
    if market_context.get('defensive_tilt') == 'high':
        regime_summary += ' 防守型候選權重偏高。'

    summary += f" Outcome loop：observed {observed_outcomes} / pending {pending_outcomes} / insufficient {insufficient_outcomes}。"
    if context_weights.get('weights'):
        summary += f" Context weights：{context_weights.get('weights')}。"
    summary += f" {regime_summary}"
    summary += f" 盤感輔助層：{tape_context.get('tape_summary')}（market_bias={tape_context.get('market_bias')}）。"
    summary += f" Experiments：active {active_experiments}。"

    payload = {
        'reviewed_at': now.isoformat(),
        'mode': args.mode,
        'count': len(recent),
        'major_event_triggered': major_event.get('triggered', False),
        'pending_outcomes': pending_outcomes,
        'observed_outcomes': observed_outcomes,
        'insufficient_outcomes': insufficient_outcomes,
        'active_experiments': active_experiments,
        'regime_review': regime_summary,
        'summary': summary,
    }
    safe_append_jsonl(REVIEW_LOG_PATH, payload)
    print('AUTO_DECISION_REVIEW_OK')
    print(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
