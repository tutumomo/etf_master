#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ai_quality_hooks import build_quality_hooks


def build_ai_decision_quality_payload(state_dir: Path) -> dict:
    hooks = build_quality_hooks(state_dir, limit=20)
    reviewed = hooks.get('reviewed_preview_buy_count', 0)
    superseded = hooks.get('superseded_preview_buy_count', 0)
    total = reviewed + superseded
    reviewed_rate = (reviewed / total) if total else 0.0
    superseded_rate = (superseded / total) if total else 0.0
    # Layered review quality scores (0-100)
    # Primary source: decision_quality.json computed by score_decision_quality.py
    decision_quality_path = state_dir / 'decision_quality.json'
    decision_quality = {}
    if decision_quality_path.exists():
        try:
            decision_quality = json.loads(decision_quality_path.read_text(encoding='utf-8'))
        except Exception:
            decision_quality = {}

    # Fallback heuristic when decision_quality.json is missing
    # - early: proxy by reviewed_rate (process discipline)
    # - short/mid: slightly discounted until we have window-specific outcome-based scoring
    early_q = int(round(reviewed_rate * 100))
    short_q = max(0, min(100, early_q - 10))
    mid_q = max(0, min(100, early_q - 15))

    if decision_quality:
        # If a future version provides window-specific quality, prefer it.
        early_q = int(decision_quality.get('direction_score', early_q))
        short_q = int(decision_quality.get('strategy_alignment_score', short_q))
        mid_q = int(decision_quality.get('confidence_calibration_score', mid_q))

    return {
        'updated_at': datetime.now().astimezone().isoformat(),
        'confidence_bias': hooks.get('confidence_bias', 'neutral'),
        'quality_summary': hooks.get('quality_summary', 'no quality summary'),
        'superseded_preview_buy_count': superseded,
        'reviewed_preview_buy_count': reviewed,
        'reviewed_rate': reviewed_rate,
        'superseded_rate': superseded_rate,
        'early_review_quality': early_q,
        'short_review_quality': short_q,
        'mid_review_quality': mid_q,
        'confidence_calibration_hint': hooks.get('confidence_bias', 'neutral'),
        'quality_inputs': {
            'decision_quality_present': bool(decision_quality),
            'decision_quality_path': str(decision_quality_path),
        },
        'source': 'ai_decision_quality_state',
    }


def write_ai_decision_quality_state(state_dir: Path) -> dict:
    payload = build_ai_decision_quality_payload(state_dir)
    path = state_dir / 'ai_decision_quality.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload
