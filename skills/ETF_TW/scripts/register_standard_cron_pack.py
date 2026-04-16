#!/usr/bin/env python3
from __future__ import annotations

"""Register ETF_TW Standard Cron Pack.

Goal:
- New machine / new instance can be set up with a single, auditable entrypoint.
- Avoid manual legacy cron drift.
- Ensure cross-machine stable runner usage (run_etf_tw_task.py) and dedupe by stable keys.

Usage:
  python3 scripts/register_standard_cron_pack.py <instance_id> --dry-run true
  python3 scripts/register_standard_cron_pack.py <instance_id> --dry-run false

Notes:
- Hermes mode should land jobs through the Hermes cron toolchain.
- Dedupe uses live cron list (agentId == instance_id OR None) + dedupe_key extraction.
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

ETF_TW_ROOT = Path(__file__).resolve().parents[1]


def cron_list_payload(agent_id: str):
    return {"jobs": []}


def extract_dedupe_keys(payload) -> set[str]:
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
    if not isinstance(jobs, list):
        return set()
    keys: set[str] = set()
    for j in jobs:
        if not isinstance(j, dict):
            continue
        meta = j.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("dedupe_key"):
            keys.add(str(meta.get("dedupe_key")))
            continue
        # fallback: parse from message
        payload_obj = j.get("payload") or {}
        msg = payload_obj.get("message") if isinstance(payload_obj, dict) else None
        if isinstance(msg, str) and "dedupe_key=" in msg:
            try:
                k = msg.split("dedupe_key=", 1)[1].split()[0].strip().strip(",").strip(".")
                if k:
                    keys.add(k)
            except Exception:
                pass
    return keys


def cron_add_job(job: dict) -> dict:
    """Legacy CLI landing is disabled in Hermes mode."""
    return {
        "ok": False,
        "stdout": "",
        "stderr": "Hermes 模式已停用舊版 CLI 註冊鏈；請改用 Hermes cronjob tool 或 `hermes cron create`。",
        "job": job,
    }


def build_standard_jobs(instance_id: str) -> list[dict]:
    # Prefer Hermes profile paths in cron payload:
    # - avoid /Users/<name>/... hardcoding
    # - keep all tasks anchored to the active Hermes ETF_TW skill tree
    # - use relative .venv/bin/python + scripts/... to satisfy exec preflight
    repo_root = "~/.hermes/profiles/etf_master/skills/ETF_TW"
    state_dir = f"instances/{instance_id}/state"

    def py(script_name: str, extra: str = "") -> str:
        base = f"cd {repo_root} && .venv/bin/python scripts/run_etf_tw_task.py"
        task = script_name.removesuffix('.py')
        return (f"{base} {task} {state_dir}" + (" " + extra if extra else "")).strip()

    def runner(task: str, extra: str = "") -> str:
        base = f"cd {repo_root} && .venv/bin/python scripts/run_etf_tw_task.py {task} {state_dir}"
        return (base + (" " + extra if extra else "")).strip()

    def job(name: str, schedule: dict, message: str, dedupe_key: str, timeout: int = 300) -> dict:
        return {
            "agentId": instance_id,
            "name": name,
            "enabled": True,
            "sessionTarget": "isolated",
            "schedule": schedule,
            "payload": {
                "kind": "agentTurn",
                "message": message + f" ; dedupe_key={dedupe_key}",
                "timeoutSeconds": timeout,
            },
            "metadata": {
                "dedupe_key": dedupe_key,
                "cron_pack": "standard",
                "instance_id": instance_id,
            },
        }

    jobs: list[dict] = []

    # Monitoring refresh + summaries (cron)
    jobs.append(job(
        name="ETF watchlist 盤前摘要",
        schedule={"kind": "cron", "expr": "45 8 * * 1-5", "tz": "Asia/Taipei"},
        message=(
            f"{runner('refresh_monitoring_state')} && "
            f".venv/bin/python scripts/generate_watchlist_summary.py --mode am"
        ),
        dedupe_key=f"cronpack::{instance_id}::watchlist_am",
        timeout=300,
    ))

    jobs.append(job(
        name="ETF watchlist 盤後摘要",
        schedule={"kind": "cron", "expr": "0 15 * * 1-5", "tz": "Asia/Taipei"},
        message=(
            f"{runner('refresh_monitoring_state')} && "
            f".venv/bin/python scripts/generate_watchlist_summary.py --mode pm"
        ),
        dedupe_key=f"cronpack::{instance_id}::watchlist_pm",
        timeout=300,
    ))

    # Decision engine orchestrator
    jobs.append(job(
        name="ETF auto decision scan driver",
        schedule={"kind": "cron", "expr": "*/30 9-13 * * 1-5", "tz": "Asia/Taipei"},
        message=py("refresh_decision_engine_state.py"),
        dedupe_key=f"cronpack::{instance_id}::decision_scan",
        timeout=300,
    ))

    # Context refreshes
    jobs.append(job(
        name="ETF Taiwan market context refresh",
        schedule={"kind": "cron", "expr": "*/30 9-13 * * 1-5", "tz": "Asia/Taipei"},
        message=py("generate_taiwan_market_context.py"),
        dedupe_key=f"cronpack::{instance_id}::taiwan_market_context",
        timeout=300,
    ))

    jobs.append(job(
        name="ETF external event context refresh",
        schedule={"kind": "cron", "expr": "*/30 9-13 * * 1-5", "tz": "Asia/Taipei"},
        message=py("generate_market_event_context.py"),
        dedupe_key=f"cronpack::{instance_id}::market_event_context",
        timeout=300,
    ))

    jobs.append(job(
        name="ETF auto decision major-event check",
        schedule={"kind": "cron", "expr": "*/30 9-13 * * 1-5", "tz": "Asia/Taipei"},
        message=py("check_major_event_trigger.py"),
        dedupe_key=f"cronpack::{instance_id}::major_event_check",
        timeout=300,
    ))

    # Quality + reviews
    jobs.append(job(
        name="ETF auto decision quality scoring",
        schedule={"kind": "cron", "expr": "30 15 * * 1-5", "tz": "Asia/Taipei"},
        message=py("score_decision_quality.py"),
        dedupe_key=f"cronpack::{instance_id}::quality_scoring",
        timeout=300,
    ))

    jobs.append(job(
        name="ETF auto decision daily review",
        schedule={"kind": "cron", "expr": "10 15 * * 1-5", "tz": "Asia/Taipei"},
        message=py("review_auto_decisions.py", "--mode daily"),
        dedupe_key=f"cronpack::{instance_id}::daily_review",
        timeout=300,
    ))

    jobs.append(job(
        name="ETF auto decision weekly review",
        schedule={"kind": "cron", "expr": "0 9 * * 6", "tz": "Asia/Taipei"},
        message=py("review_auto_decisions.py", "--mode weekly"),
        dedupe_key=f"cronpack::{instance_id}::weekly_review",
        timeout=300,
    ))

    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_id")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    args = ap.parse_args()

    instance_id = args.instance_id
    dry_run = args.dry_run == "true"

    os.environ["OPENCLAW_AGENT_NAME"] = instance_id

    jobs = build_standard_jobs(instance_id)
    live = cron_list_payload(instance_id)
    existing = extract_dedupe_keys(live)
    pending = [j for j in jobs if j.get("metadata", {}).get("dedupe_key") not in existing]

    results = []
    if not dry_run:
        for j in pending:
            results.append(cron_add_job(j))

    out = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "instance_id": instance_id,
        "dry_run": dry_run,
        "jobs": jobs,
        "existing_dedupe_keys": sorted(existing),
        "pending_jobs": pending,
        "results": results,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
