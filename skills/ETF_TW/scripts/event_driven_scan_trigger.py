#!/usr/bin/env python3
from __future__ import annotations
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

"""
event_driven_scan_trigger.py — P6 事件驅動掃描觸發器

當 major_event_flag.json 顯示 L2/L3 事件且 should_notify=True 時，
立即觸發 run_auto_decision_scan，無需等待下一次定時 cron。

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/event_driven_scan_trigger.py

Exit codes:
    0 — success (triggered, skipped, or no event)
    1 — scan was triggered but returned non-zero
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from etf_core.state_io import safe_load_json, atomic_save_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

TW_TZ = ZoneInfo('Asia/Taipei')

TRIGGER_LEVELS = frozenset({'L2', 'L3'})


def should_trigger_scan(event_flag: dict, event_state: dict) -> tuple[bool, str]:
    """Pure function: decides if scan should be triggered.

    Returns (should_trigger: bool, reason: str)
    """
    if not event_flag.get('triggered'):
        return False, 'no_event'

    level = event_flag.get('level', 'none')
    if level not in TRIGGER_LEVELS:
        return False, f'level_too_low:{level}'

    if not event_flag.get('should_notify'):
        return False, 'already_notified_same_hash'

    # Check cooldown: same event hash already triggered scan
    current_hash = event_flag.get('event_hash')
    last_triggered_hash = event_state.get('event_scan_triggered_hash')
    if current_hash and current_hash == last_triggered_hash:
        return False, 'already_triggered_this_event'

    return True, f'event_{level}'


def run_decision_scan(root: Path) -> int:
    """Invoke run_auto_decision_scan.py via venv python. Returns exit code."""
    venv_python = root / '.venv' / 'bin' / 'python3'
    if not venv_python.exists():
        venv_python = Path(sys.executable)
    scan_script = root / 'scripts' / 'run_auto_decision_scan.py'
    result = subprocess.run(
        [str(venv_python), str(scan_script)],
        cwd=str(root),
        timeout=120,
    )
    return result.returncode


def main() -> int:
    try:
        STATE = context.get_state_dir()

        event_flag = safe_load_json(STATE / 'major_event_flag.json', {})
        event_state = safe_load_json(STATE / 'event_review_state.json', {})

        trigger, reason = should_trigger_scan(event_flag, event_state)

        if not trigger:
            print(f'EVENT_DRIVEN_SCAN_SKIPPED:reason={reason}')
            return 0

        level = event_flag.get('level', 'unknown')
        current_hash = event_flag.get('event_hash')

        # Mark as triggered BEFORE calling scan to prevent race conditions
        now_iso = datetime.now(TW_TZ).isoformat()
        event_state['event_scan_triggered_at'] = now_iso
        event_state['event_scan_triggered_hash'] = current_hash
        event_state['event_scan_triggered_level'] = level
        atomic_save_json(STATE / 'event_review_state.json', event_state)

        print(f'EVENT_DRIVEN_SCAN_TRIGGERED:level={level}')

        rc = run_decision_scan(ROOT)
        if rc != 0:
            print(f'EVENT_DRIVEN_SCAN_FAILED:rc={rc}')
            return 1

        return 0

    except Exception as exc:
        print(f'EVENT_DRIVEN_SCAN_SKIPPED:reason=exception:{exc}')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
