#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def build_registration_records(plan: dict) -> list[dict]:
    request_id = plan.get('request_id')
    runner = (plan.get('binding') or {}).get('runner')
    rows = []
    for window in plan.get('windows', []):
        row = {
            'request_id': request_id,
            'review_window': window.get('name'),
            'review_window_label': window.get('label'),
            'offset_trading_days': window.get('offset_trading_days'),
            'runner': runner,
            'dedupe_key': f"{request_id}::{window.get('name')}",
            'status': 'draft',
        }
        rows.append(row)
    return rows


def write_registration_records(state_dir: Path, plan: dict) -> list[dict]:
    # Attach instance identity for cron namespacing (avoid hardcoding etf_master).
    import os
    instance_id = os.environ.get('AGENT_ID') or os.environ.get('OPENCLAW_AGENT_NAME')
    rows = build_registration_records(plan)
    if instance_id:
        for r in rows:
            r['instance_id'] = instance_id
    (state_dir / 'layered_review_registrations.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    for row in rows:
        _append_jsonl(state_dir / 'layered_review_registrations.jsonl', row)
    return rows
