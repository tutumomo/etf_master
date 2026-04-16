#!/usr/bin/env python3
from __future__ import annotations

"""Cross-machine stable runner for ETF_TW cron tasks.

Why:
- Avoid hardcoding install paths like /workspace/... or /Users/... in cron payloads.
- Avoid hardcoding venv interpreter paths; cron can call this script with whatever python is available.

Usage:
  python3 scripts/run_etf_tw_task.py <task> [task-args...]

Supported tasks (stable contract):
- auto_post_review_cycle <state_dir> --request-id ... --review-window ... [--outcome-note ...]
- refresh_monitoring_state [<state_dir>]
- refresh_decision_engine_state [<state_dir>]
- generate_taiwan_market_context [<state_dir>]
- generate_market_event_context [<state_dir>]
- check_major_event_trigger [<state_dir>]
- score_decision_quality [<state_dir>]
- review_auto_decisions [<state_dir>] --mode <daily|weekly>

Notes:
- Many underlying scripts resolve instance state from AGENT_ID (legacy OPENCLAW_AGENT_NAME also accepted).
  If you pass a state_dir like instances/<instance_id>/state, this runner will derive and set AGENT_ID.
"""

import os
import subprocess
import sys
from pathlib import Path

ETF_TW_ROOT = Path(__file__).resolve().parents[1]


def _maybe_set_agent_from_state_dir(args: list[str]) -> list[str]:
    """If first arg looks like a state_dir, set AGENT_ID (and legacy fallback) and drop it from argv."""
    if not args:
        return args

    try:
        p = Path(args[0]).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        # Expect .../instances/<agent_id>/state
        if p.name == "state" and p.parent.parent.name == "instances":
            agent_id = p.parent.name
            os.environ["AGENT_ID"] = agent_id
            return args[1:]
    except Exception:
        pass

    return args


def _run_script(script_name: str, args: list[str]) -> int:
    script = str(ETF_TW_ROOT / "scripts" / script_name)
    cmd = [sys.executable, script, *args]
    proc = subprocess.run(cmd, cwd=str(ETF_TW_ROOT), env=os.environ.copy())
    return int(proc.returncode)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_etf_tw_task.py <task> [args...]", file=sys.stderr)
        return 2

    task = sys.argv[1]
    args = sys.argv[2:]

    # Ensure local imports work regardless of cwd.
    sys.path.insert(0, str(ETF_TW_ROOT))

    # Set agent identity from optional state_dir prefix.
    args = _maybe_set_agent_from_state_dir(args)

    if task == "auto_post_review_cycle":
        return _run_script("auto_post_review_cycle.py", args)

    # Monitoring / context refresh tasks used by standard cron pack.
    if task == "refresh_monitoring_state":
        return _run_script("refresh_monitoring_state.py", args)
    if task == "refresh_decision_engine_state":
        return _run_script("refresh_decision_engine_state.py", args)
    if task == "generate_taiwan_market_context":
        return _run_script("generate_taiwan_market_context.py", args)
    if task == "generate_market_event_context":
        return _run_script("generate_market_event_context.py", args)
    if task == "check_major_event_trigger":
        return _run_script("check_major_event_trigger.py", args)
    if task == "score_decision_quality":
        return _run_script("score_decision_quality.py", args)
    if task == "review_auto_decisions":
        return _run_script("review_auto_decisions.py", args)

    print(f"Unknown task: {task}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
