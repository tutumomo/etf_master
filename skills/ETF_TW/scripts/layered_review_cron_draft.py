#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))


def build_layered_review_cron_jobs(plan: dict) -> list[dict]:
    request_id = plan.get('request_id')
    runner = (plan.get('binding') or {}).get('runner')
    jobs = []
    for window in plan.get('windows', []):
        jobs.append({
            'request_id': request_id,
            'review_window': window.get('name'),
            'review_window_label': window.get('label'),
            'offset_trading_days': window.get('offset_trading_days'),
            'runner': runner,
            'mode': 'future-cron-draft',
        })
    return jobs


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('usage: layered_review_cron_draft.py <plan-json-path>')
    path = Path(sys.argv[1])
    plan = json.loads(path.read_text(encoding='utf-8'))
    print(json.dumps(build_layered_review_cron_jobs(plan), ensure_ascii=False, indent=2))
