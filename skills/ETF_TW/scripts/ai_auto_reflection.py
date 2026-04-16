#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from scripts.ai_reflection_lifecycle import record_reflection


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def auto_reflect_if_ready(state_dir: Path):
    response = _load_json(state_dir / 'ai_decision_response.json')
    review = response.get('review') or {}
    if review.get('status') not in {'reviewed', 'superseded'}:
        return None
    candidate = response.get('candidate') or {}
    decision = response.get('decision') or {}
    symbol = candidate.get('symbol') or 'unknown-symbol'
    action = decision.get('action') or 'unknown-action'
    note = f"auto-reflection: {symbol} / {action} / review={review.get('status')}"
    if review.get('status') == 'reviewed':
        note += ' / 此類建議目前可保留觀察。'
    if review.get('status') == 'superseded':
        note += ' / 此類建議近期容易被新版取代，後續應降低信心或延後下結論。'
    if review.get('human_feedback'):
        note += f" / feedback={review.get('human_feedback')}"
    return record_reflection(state_dir, reflection_note=note)
