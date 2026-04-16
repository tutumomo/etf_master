#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from layered_review_windows import get_layered_review_windows


def build_layered_review_schedule_plan(request_id: str, runner: str = 'scripts/auto_post_review_cycle.py') -> dict:
    return {
        'request_id': request_id,
        'windows': get_layered_review_windows(),
        'binding': {
            'runner': runner,
            'state_artifact': 'ai_decision_response.json',
            'schedule_kind': 'future-cron-hook',
        },
        'notes': [
            'T+1 only for early review, not final judgment',
            'T+3/T+10 should progressively strengthen outcome interpretation',
        ],
    }


if __name__ == '__main__':
    request_id = sys.argv[1] if len(sys.argv) > 1 else 'missing-request-id'
    print(json.dumps(build_layered_review_schedule_plan(request_id), ensure_ascii=False, indent=2))
