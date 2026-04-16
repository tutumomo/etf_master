#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from ai_quality_hooks import build_quality_hooks


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def build_decision_memory_context(state_dir: Path, limit: int = 5) -> dict:
    reviews = _read_jsonl(state_dir / 'ai_decision_review.jsonl')
    outcomes = _read_jsonl(state_dir / 'ai_decision_outcome.jsonl')
    reflections = _read_jsonl(state_dir / 'ai_decision_reflection.jsonl')

    recent_reviews = reviews[-limit:]
    recent_outcomes = outcomes[-limit:]
    recent_reflections = reflections[-limit:]

    notes = []
    for row in recent_reflections:
        notes.append({
            'request_id': row.get('request_id'),
            'symbol': row.get('symbol'),
            'reflection_note': row.get('reflection_note'),
            'review_status': row.get('review_status'),
            'outcome_status': row.get('outcome_status'),
        })

    quality_hooks = build_quality_hooks(state_dir, limit=limit)
    return {
        'recent_review_count': len(recent_reviews),
        'recent_outcome_count': len(recent_outcomes),
        'recent_reflection_count': len(recent_reflections),
        'memory_notes': notes,
        'quality_hooks': quality_hooks,
    }
