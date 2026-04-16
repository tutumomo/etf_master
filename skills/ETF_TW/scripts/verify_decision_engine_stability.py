#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import sys

from etf_core.state_schema import REQUIRED_KEYS

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()

REQUIRED_FILES = [
    'market_event_context.json',
    'market_context_taiwan.json',
    'major_event_flag.json',
    'event_review_state.json',
    'decision_quality.json',
    'auto_trade_config.json',
    'auto_trade_state.json',
]
FILE_KIND_MAP = {
    'market_event_context.json': 'market_event_context',
    'market_context_taiwan.json': 'market_context_taiwan',
    'major_event_flag.json': 'major_event_flag',
    'event_review_state.json': 'event_review_state',
    'decision_quality.json': 'decision_quality',
    'auto_trade_config.json': 'auto_trade_config',
    'auto_trade_state.json': 'auto_trade_state',
}


def main() -> int:
    subprocess.check_call([str(ROOT / '.venv' / 'bin' / 'python'), str(ROOT / 'scripts' / 'refresh_decision_engine_state.py')], cwd=str(ROOT))
    warnings = []
    for name in REQUIRED_FILES:
        path = STATE / name
        assert path.exists(), f'missing: {name}'
        payload = json.loads(path.read_text(encoding='utf-8'))
        kind = FILE_KIND_MAP[name]
        missing = [key for key in REQUIRED_KEYS.get(kind, []) if key not in payload]
        if missing:
            warnings.append(f'{name}: missing keys {missing}')
    print('DECISION_ENGINE_STABILITY_OK')
    if warnings:
        print('VERIFY_WARNINGS')
        for w in warnings:
            print(w)
    else:
        print('VERIFY_SCHEMA_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
