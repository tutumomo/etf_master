#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from provenance_logger import find_provenance_by_decision_id, update_review_lifecycle

TW_TZ = ZoneInfo('Asia/Taipei')


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _load_jsonl_last_matching(path: Path, request_id: str) -> dict:
    if not path.exists():
        return {}
    last = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get('request_id') == request_id:
            last = obj
    return last


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def _add_provenance_reflection_tag(state_dir: Path, request_id: str, reflection_note: str):
    """Tag provenance record with reflection info."""
    provenance_path = state_dir / 'decision_provenance.jsonl'
    try:
        from etf_core.state_io import safe_load_jsonl as _load_jsonl
        rows = _load_jsonl(provenance_path)
        found = False
        for row in rows:
            if row.get('decision_id') == request_id:
                tags = row.get('tags', [])
                # Add reflection tag if not already present
                tag = f"reflection:{reflection_note[:50]}"
                if tag not in tags:
                    tags.append(tag)
                    row['tags'] = tags
                    found = True
                break
        if found:
            provenance_path.parent.mkdir(parents=True, exist_ok=True)
            provenance_path.write_text(
                ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows),
                encoding='utf-8',
            )
    except Exception as e:
        import warnings
        warnings.warn(f"[provenance] Failed to tag reflection: {e}")


def record_reflection(state_dir: Path, reflection_note: str) -> dict:
    response_path = state_dir / 'ai_decision_response.json'
    outcome_path = state_dir / 'ai_decision_outcome.jsonl'
    reflection_path = state_dir / 'ai_decision_reflection.jsonl'

    response = _load_json(response_path)
    request_id = response.get('request_id')
    outcome = _load_jsonl_last_matching(outcome_path, request_id) if request_id else {}

    row = {
        'request_id': request_id,
        'recorded_at': datetime.now(TW_TZ).isoformat(),
        'source': response.get('source'),
        'symbol': (response.get('candidate') or {}).get('symbol'),
        'action': (response.get('decision') or {}).get('action'),
        'summary': (response.get('decision') or {}).get('summary'),
        'review_status': (response.get('review') or {}).get('status', 'unknown'),
        'outcome_status': outcome.get('outcome_status', 'unknown'),
        'reflection_note': reflection_note,
        'human_feedback': (response.get('review') or {}).get('human_feedback'),
        'outcome_note': outcome.get('outcome_note'),
    }
    _append_jsonl(reflection_path, row)

    # --- Provenance: tag with reflection ---
    if request_id:
        _add_provenance_reflection_tag(state_dir, request_id, reflection_note)

    return row
