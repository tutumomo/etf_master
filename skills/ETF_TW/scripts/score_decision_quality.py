#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, atomic_save_json
from etf_core.state_schema import validate_state_payload

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
DECISION_LOG_PATH = STATE / 'decision_log.jsonl'
QUALITY_PATH = STATE / 'decision_quality.json'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
EVENT_CONTEXT_PATH = STATE / 'market_event_context.json'


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    now = datetime.now(TW_TZ)
    logs = load_jsonl(DECISION_LOG_PATH)
    recent = []
    for row in logs:
        ts = datetime.fromisoformat(row['scanned_at'])
        if now - ts <= timedelta(days=7):
            recent.append(row)

    total = len(recent)
    buy_preview = sum(1 for r in recent if r.get('action') == 'buy-preview')
    hold_count = sum(1 for r in recent if r.get('action') == 'hold')
    anomaly_hits = sum(1 for r in recent if r.get('anomalies'))

    market_context = validate_state_payload('market_context_taiwan', safe_load_json(MARKET_CONTEXT_PATH, {'context_summary': '尚無台灣市場情勢摘要', 'risk_temperature': 'normal', 'market_regime': 'unknown'}), {'market_regime': 'unknown', 'risk_temperature': 'normal', 'context_summary': '尚無台灣市場情勢摘要'})
    event_context = validate_state_payload('market_event_context', safe_load_json(EVENT_CONTEXT_PATH, {'summary': '尚無外部事件情境摘要', 'global_risk_level': 'unknown', 'geo_political_risk': 'unknown', 'event_regime': 'unknown'}), {'event_regime': 'unknown', 'global_risk_level': 'unknown', 'summary': '尚無外部事件情境摘要'})
    min_sample_required = 20
    sample_ready = total >= min_sample_required
    direction_score = 50 if total == 0 else max(0, min(100, 50 + buy_preview * 2 - anomaly_hits * 3))
    risk_score = 60 if anomaly_hits == 0 else max(0, 60 - anomaly_hits * 5)
    opportunity_score = 40 if buy_preview == 0 else min(100, 40 + buy_preview * 4)
    strategy_alignment_score = 65 if total == 0 else min(100, 55 + hold_count)
    confidence_calibration_score = 50 if total == 0 else min(100, 50 + (total - anomaly_hits))

    if market_context.get('risk_temperature') == 'elevated':
        risk_score = max(0, risk_score - 5)
        confidence_calibration_score = max(0, confidence_calibration_score - 3)
    if market_context.get('income_tilt') == 'high':
        opportunity_score = min(100, opportunity_score + 3)
    if market_context.get('defensive_tilt') == 'high':
        strategy_alignment_score = min(100, strategy_alignment_score + 2)
    if event_context.get('global_risk_level') == 'elevated':
        risk_score = max(0, risk_score - 3)
    if event_context.get('geo_political_risk') == 'high':
        confidence_calibration_score = max(0, confidence_calibration_score - 2)

    payload = {
        'evaluated_at': now.isoformat(),
        'window_days': 7,
        'decision_count': total,
        'buy_preview_count': buy_preview,
        'hold_count': hold_count,
        'anomaly_hit_count': anomaly_hits,
        'direction_score': direction_score,
        'risk_score': risk_score,
        'opportunity_score': opportunity_score,
        'strategy_alignment_score': strategy_alignment_score,
        'confidence_calibration_score': confidence_calibration_score,
        'min_sample_required': min_sample_required,
        'sample_ready': sample_ready,
        'sample_guardrail': '樣本不足，僅供觀察' if not sample_ready else '樣本量已達基本觀察門檻',
        'market_context_summary': market_context.get('context_summary'),
        'event_context_summary': event_context.get('summary'),
        'quality_summary': (
            f'最近 7 天共 {total} 次決策，buy-preview {buy_preview} 次，hold {hold_count} 次，'
            f'異常命中 {anomaly_hits} 次。此為第一版校正骨架，僅供趨勢觀察。'
        ),
        'source': 'score_decision_quality',
    }
    saved_path = atomic_save_json(QUALITY_PATH, payload)
    print('DECISION_QUALITY_OK')
    print(f'SAVED:{saved_path}')
    print(payload['quality_summary'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
