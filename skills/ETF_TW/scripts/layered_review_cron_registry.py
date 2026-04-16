#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def compute_jobs_to_add(jobs: list[dict], existing_dedupe_keys: set[str]) -> list[dict]:
    pending = []
    for job in jobs:
        key = ((job.get('metadata') or {}).get('dedupe_key'))
        if not key or key in existing_dedupe_keys:
            continue
        pending.append(job)
    return pending


def list_existing_dedupe_keys(registry_path: Path) -> set[str]:
    if not registry_path.exists():
        return set()
    try:
        payload = json.loads(registry_path.read_text(encoding='utf-8'))
    except Exception:
        return set()
    keys = set()
    for item in payload:
        key = ((item.get('metadata') or {}).get('dedupe_key'))
        if key:
            keys.add(key)
    return keys


def add_jobs_via_cron_tool(jobs: list[dict], dry_run: bool = True) -> list[dict]:
    results = []
    for job in jobs:
        if dry_run:
            results.append({'ok': True, 'dry_run': True, 'job': job})
            continue
        results.append({
            'ok': False,
            'job': job,
            'stdout': '',
            'stderr': 'Hermes 模式已停用舊版 CLI 註冊鏈；請改用 Hermes cronjob tool 或 `hermes cron create`。',
        })
    return results
