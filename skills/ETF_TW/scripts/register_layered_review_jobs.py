#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'scripts'))

from layered_review_cron_jobs import build_cron_job_payloads
from layered_review_cron_registration import write_registration_records
from layered_review_cron_registry import add_jobs_via_cron_tool, compute_jobs_to_add, list_existing_dedupe_keys
from layered_review_cron_registry_live import cron_add_job, cron_list_payload, extract_dedupe_keys_from_cron_list
from instance_identity import get_instance_id_fallback


def register_from_plan(state_dir: Path, plan: dict, dry_run: bool = True) -> dict:
    rows = write_registration_records(state_dir, plan)
    jobs = build_cron_job_payloads(rows)
    registry_path = state_dir / 'layered_review_cron_jobs.json'
    local_existing = list_existing_dedupe_keys(registry_path)

    # P5 hardening: live cron list is the primary source of dedupe truth.
    # Local registry is best-effort only and must not create false-positive blocks.
    instance_id = get_instance_id_fallback()
    live_existing = extract_dedupe_keys_from_cron_list(cron_list_payload(agent_id=instance_id))

    # For transparency: show both, but gate primarily on live.
    existing = live_existing | local_existing
    pending_jobs = compute_jobs_to_add(jobs, live_existing)
    if dry_run:
        results = add_jobs_via_cron_tool(pending_jobs, dry_run=True)
    else:
        # Use live CLI add; results include stdout/stderr/cmd and are stored in the return JSON.
        results = [cron_add_job(job) for job in pending_jobs]
    if jobs:
        registry_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')
    return {
        'dry_run': dry_run,
        'registrations': rows,
        'jobs': jobs,
        'pending_jobs': pending_jobs,
        'results': results,
        'existing_dedupe_keys': sorted(existing),
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('state_dir')
    parser.add_argument('plan_json_path')
    parser.add_argument('--dry-run', dest='dry_run', default='true', help='true|false (default: true)')
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    plan = json.loads(Path(args.plan_json_path).read_text(encoding='utf-8'))
    dry_run = str(args.dry_run).lower() != 'false'

    print(json.dumps(register_from_plan(state_dir, plan, dry_run=dry_run), ensure_ascii=False, indent=2))
