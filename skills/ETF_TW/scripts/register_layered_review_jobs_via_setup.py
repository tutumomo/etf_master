#!/usr/bin/env python3
from __future__ import annotations

"""Non-interactive helper: write plan + register layered review cron jobs for an instance.

This is meant to be called by setup_agent.py (optional) or power users.

Usage:
  python3 scripts/register_layered_review_jobs_via_setup.py <instance_id> <request_id>

It will:
- ensure instances/<instance_id>/state exists
- export OPENCLAW_AGENT_NAME for downstream scripts
- write layered_review_plan.json
- register cron jobs (dry-run false)
- write instances/<instance_id>/state/layered_review_cron_last_run.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.write_layered_review_plan import write_layered_review_plan
from scripts.register_layered_review_jobs import register_from_plan


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: register_layered_review_jobs_via_setup.py <instance_id> <request_id>")
        return 2

    instance_id = sys.argv[1]
    request_id = sys.argv[2]

    os.environ["OPENCLAW_AGENT_NAME"] = instance_id
    state_dir = ROOT / "instances" / instance_id / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    plan = write_layered_review_plan(state_dir, request_id)
    out = register_from_plan(state_dir, plan, dry_run=False)

    last_run = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "instance_id": instance_id,
        "request_id": request_id,
        "dry_run": False,
        "pending_jobs": [j.get("name") for j in out.get("pending_jobs", [])],
        "results": out.get("results", []),
    }
    (state_dir / "layered_review_cron_last_run.json").write_text(
        json.dumps(last_run, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(last_run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
