#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

def build_cron_job_payloads(rows: list[dict], session_target: str = 'isolated') -> list[dict]:
    jobs = []
    for row in rows:
        request_id = row.get('request_id')
        review_window = row.get('review_window')
        offset_days = row.get('offset_trading_days')
        label = row.get('review_window_label')
        dedupe_key = row.get('dedupe_key')
        instance_id = row.get('instance_id') or row.get('agent_id') or row.get('agentId')
        etf_root = Path(__file__).resolve().parents[1]
        state_path = etf_root / 'instances' / (instance_id or 'UNKNOWN') / 'state'
        runner_cmd = (
            f"python3 {etf_root}/scripts/auto_post_review_cycle.py {state_path} "
            f"--request-id {request_id} --review-window {review_window} --outcome-note \"{label}｜auto\""
        )

        jobs.append({
            # Important: do not hardcode. Prefer instance_id/agent_id propagated by registration records.
            'agentId': instance_id,
            'name': f'ETF layered review {request_id} {review_window}',
            'sessionTarget': session_target,
            'schedule': {
                'kind': 'every',
                'everyMs': 86400000,
            },
            'payload': {
                'kind': 'agentTurn',
                'message': (
                    'ETF_TW layered review runner (do not place trades). ' +
                    f'Run: {runner_cmd} ; ' +
                    f'dedupe_key={dedupe_key}'
                ),
                'timeoutSeconds': 120,
            },
            'delivery': {
                'mode': 'announce'
            },
            'metadata': {
                'request_id': request_id,
                'review_window': review_window,
                'dedupe_key': dedupe_key,
                'runner': str(etf_root / 'scripts' / 'auto_post_review_cycle.py'),
                'registration_status': row.get('status'),
            }
        })
    return jobs
