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
EXPERIMENTS_PATH = STATE / 'decision_experiments.json'
OUTCOME_SUMMARY_PATH = STATE / 'decision_outcome_summary.json'
QUALITY_PATH = STATE / 'decision_quality.json'


def main() -> int:
    now = datetime.now(TW_TZ)
    payload = safe_load_json(EXPERIMENTS_PATH, {'experiments': [], 'status': 'bootstrap'})
    outcome = safe_load_json(OUTCOME_SUMMARY_PATH, {'observed': 0, 'pending': 0, 'insufficient_data': 0})
    quality = safe_load_json(QUALITY_PATH, {'direction_score': 50, 'risk_score': 50})

    total = outcome.get('total', 0)
    observed = outcome.get('observed', 0)
    insufficient = outcome.get('insufficient_data', 0)
    direction = quality.get('direction_score', 50)
    risk = quality.get('risk_score', 50)

    status = 'observe-more'
    rationale = '樣本仍少，繼續觀察'
    if total >= 5 and observed >= max(1, total // 2) and direction >= 55 and risk >= 55:
        status = 'keep-candidate'
        rationale = '樣本與品質分數達基本門檻，可列入 keep 候選'
    elif total >= 5 and (insufficient >= max(2, total // 2) or risk < 45):
        status = 'revert-candidate'
        rationale = '資料不足或風險分數偏弱，可列入 revert 候選'

    experiment_entry = {
        'experiment_id': 'default-decision-engine-v1',
        'rule_family': 'decision-engine-default',
        'status': status,
        'reviewed_at': now.isoformat(),
        'review_after_days': 5,
        'notes': rationale,
    }

    payload.update({
        'updated_at': now.isoformat(),
        'source': 'update_experiment_decisions',
        'status': status,
        'experiments': [experiment_entry],
    })
    atomic_save_json(EXPERIMENTS_PATH, payload)
    print('EXPERIMENT_DECISION_UPDATE_OK')
    print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
