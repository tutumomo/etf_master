#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    'refresh_monitoring_state.py',
    'generate_market_event_context.py',
    'generate_taiwan_market_context.py',
    'generate_intraday_tape_context.py',
    'check_major_event_trigger.py',
    'run_auto_decision_scan.py',
    'update_decision_outcomes.py',
    'build_regime_bucket_stats.py',
    'update_context_weights.py',
    'score_decision_quality.py',
    'update_experiment_decisions.py',
]


def main() -> int:
    for name in SCRIPTS:
        subprocess.check_call([sys.executable, str(ROOT / 'scripts' / name)], cwd=str(ROOT))
    print('DECISION_ENGINE_REFRESH_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
