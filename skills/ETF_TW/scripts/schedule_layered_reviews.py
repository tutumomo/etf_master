#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from layered_review_windows import get_layered_review_windows


def build_layered_review_schedule_plan() -> dict:
    return {
        'windows': get_layered_review_windows(),
        'default_runner': 'scripts/auto_post_review_cycle.py',
        'note': 'scheduler hook skeleton for future cron integration',
    }


if __name__ == '__main__':
    print(json.dumps(build_layered_review_schedule_plan(), ensure_ascii=False, indent=2))
