#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess


def extract_dedupe_keys_from_cron_list(payload) -> set[str]:
    if isinstance(payload, dict):
        payload = payload.get('jobs', [])
    if not isinstance(payload, list):
        return set()

    keys = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        job = item.get('job') or item
        if not isinstance(job, dict):
            continue

        # Dedupe key may be stored either under metadata.dedupe_key (tool-based adds)
        # or embedded in payload.message as `dedupe_key=...` (CLI-flag adds).
        metadata = job.get('metadata') or {}
        key = None

        if isinstance(metadata, dict):
            key = metadata.get('dedupe_key')

        if not key:
            payload_obj = job.get('payload') or {}
            msg = payload_obj.get('message') if isinstance(payload_obj, dict) else None
            if isinstance(msg, str) and 'dedupe_key=' in msg:
                try:
                    key = msg.split('dedupe_key=', 1)[1].split()[0].strip().strip(',').strip('.')
                except Exception:
                    key = None

        if key:
            keys.add(key)

    return keys


def cron_list_payload(agent_id: str | None = 'etf_master') -> list[dict] | dict:
    """Return cron list payload.

    Legacy CLI bridge is removed in Hermes mode; keep the return shape stable.

    IMPORTANT:
    - Some jobs (added via CLI flags) may not include agentId in the list payload.
      To avoid breaking dedupe, we *primarily* filter by agentId when present,
      but keep agentId==None jobs (they are effectively un-namespaced).
    """
    return {'jobs': []} if agent_id else []


def cron_add_job(job: dict) -> dict:
    """Add cron job via CLI.

    Hermes mode no longer lands jobs through the legacy CLI bridge.
    Returns a structured error object so callers do not silently think registration succeeded.
    """
    return {
        'ok': False,
        'stdout': '',
        'stderr': 'Hermes 模式已停用舊版 CLI 註冊鏈；請改用 Hermes cronjob tool 或 `hermes cron create`。',
        'job': job,
        'mode': 'disabled-legacy-bridge',
    }
