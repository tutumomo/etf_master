#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


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


def build_quality_hooks(state_dir: Path, limit: int = 10) -> dict:
    reflections = _read_jsonl(state_dir / 'ai_decision_reflection.jsonl')[-limit:]
    superseded_preview_buy_count = sum(1 for r in reflections if r.get('action') == 'preview_buy' and r.get('review_status') == 'superseded')
    reviewed_preview_buy_count = sum(1 for r in reflections if r.get('action') == 'preview_buy' and r.get('review_status') == 'reviewed')

    confidence_bias = 'neutral'
    if superseded_preview_buy_count >= 2:
        confidence_bias = 'lower'
    elif reviewed_preview_buy_count >= 2:
        confidence_bias = 'raise_if_supported'

    return {
        'superseded_preview_buy_count': superseded_preview_buy_count,
        'reviewed_preview_buy_count': reviewed_preview_buy_count,
        'confidence_bias': confidence_bias,
        'quality_summary': f"recent preview_buy: reviewed={reviewed_preview_buy_count}, superseded={superseded_preview_buy_count}",
    }
