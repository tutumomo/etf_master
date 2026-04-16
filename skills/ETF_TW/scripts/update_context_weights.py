#!/usr/bin/env python3
from __future__ import annotations

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
CONTEXT_WEIGHTS_PATH = STATE / 'context_weights.json'
OUTCOME_SUMMARY_PATH = STATE / 'decision_outcome_summary.json'
MARKET_CONTEXT_PATH = STATE / 'market_context_taiwan.json'
QUALITY_PATH = STATE / 'decision_quality.json'


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, round(value, 4)))


def main() -> int:
    now = datetime.now(TW_TZ)
    payload = safe_load_json(CONTEXT_WEIGHTS_PATH, {
        'weights': {
            'market_context': 1.0,
            'external_event_context': 1.0,
            'decision_quality': 1.0,
            'defensive_bias': 1.0,
        },
        'bounds': {'min': 0.5, 'max': 1.5},
    })
    outcome = safe_load_json(OUTCOME_SUMMARY_PATH, {'observed': 0, 'pending': 0, 'insufficient_data': 0})
    market_context = safe_load_json(MARKET_CONTEXT_PATH, {'market_regime': 'unknown', 'risk_temperature': 'normal', 'defensive_tilt': 'neutral', 'income_tilt': 'neutral'})
    quality = safe_load_json(QUALITY_PATH, {'risk_score': 50, 'direction_score': 50, 'confidence_calibration_score': 50})

    weights = payload.get('weights', {})
    lower = float(payload.get('bounds', {}).get('min', 0.5))
    upper = float(payload.get('bounds', {}).get('max', 1.5))
    adjustments = []

    if market_context.get('risk_temperature') == 'elevated':
        weights['defensive_bias'] = clamp(weights.get('defensive_bias', 1.0) + 0.08, lower, upper)
        adjustments.append('risk_temperature=elevated → defensive_bias +0.08')
    if market_context.get('income_tilt') == 'high':
        weights['market_context'] = clamp(weights.get('market_context', 1.0) + 0.03, lower, upper)
        adjustments.append('income_tilt=high → market_context +0.03')
    if outcome.get('insufficient_data', 0) > 0:
        weights['decision_quality'] = clamp(weights.get('decision_quality', 1.0) - 0.05, lower, upper)
        adjustments.append('insufficient_data > 0 → decision_quality -0.05')
    if quality.get('risk_score', 50) < 55:
        weights['external_event_context'] = clamp(weights.get('external_event_context', 1.0) + 0.04, lower, upper)
        adjustments.append('risk_score < 55 → external_event_context +0.04')

    payload.update({
        'updated_at': now.isoformat(),
        'source': 'update_context_weights',
        'mode': 'auto-bounded',
        'weights': weights,
        'last_adjustments': adjustments,
    })
    atomic_save_json(CONTEXT_WEIGHTS_PATH, payload)
    print('CONTEXT_WEIGHTS_UPDATE_OK')
    print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
