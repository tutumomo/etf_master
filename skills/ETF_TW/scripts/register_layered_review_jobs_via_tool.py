#!/usr/bin/env python3
from __future__ import annotations

"""Register layered review cron jobs using Hermes cron payload semantics.

Why: Hermes should treat cron registration as structured job generation, then land jobs via
the Hermes cron toolchain rather than any legacy CLI bridge.
This script produces cron job objects and prints them; the caller (agent) should use the Hermes
`cronjob` tool or `hermes cron create` flow to add them safely and verify via cron list.

Usage:
  register_layered_review_jobs_via_tool.py <state_dir> <plan_json_path>
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'scripts'))

from layered_review_cron_jobs import build_cron_job_payloads
from layered_review_cron_registration import write_registration_records
from layered_review_cron_registry_live import cron_list_payload, extract_dedupe_keys_from_cron_list
from layered_review_cron_registry import list_existing_dedupe_keys, compute_jobs_to_add


def build_pending_jobs(state_dir: Path, plan: dict) -> dict:
    rows = write_registration_records(state_dir, plan)
    jobs = build_cron_job_payloads(rows)

    registry_path = state_dir / 'layered_review_cron_jobs.json'
    local_existing = list_existing_dedupe_keys(registry_path)
    live_existing = extract_dedupe_keys_from_cron_list(cron_list_payload(agent_id='etf_master'))

    pending_jobs = compute_jobs_to_add(jobs, live_existing)

    # write local registry snapshot (audit only)
    if jobs:
        registry_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')

    return {
        'registrations': rows,
        'jobs': jobs,
        'pending_jobs': pending_jobs,
        'existing_live_dedupe_keys': sorted(live_existing),
        'existing_local_dedupe_keys': sorted(local_existing),
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('usage: register_layered_review_jobs_via_tool.py <state-dir> <plan-json-path>')
    state_dir = Path(sys.argv[1])
    plan = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    print(json.dumps(build_pending_jobs(state_dir, plan), ensure_ascii=False, indent=2))
