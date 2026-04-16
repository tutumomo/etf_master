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

from provenance_logger import update_review_lifecycle, find_provenance_by_decision_id
from etf_core.state_io import safe_load_jsonl

TW_TZ = ZoneInfo('Asia/Taipei')


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def _determine_review_window(state_dir: Path, request_id: str) -> str:
    """Determine which review window (T1/T3/T10) to fill based on decision age."""
    provenance_path = state_dir / 'decision_provenance.jsonl'
    record = find_provenance_by_decision_id(provenance_path, request_id)
    if not record:
        return 'T1'  # fallback
    lc = record.get('review_lifecycle', {})
    if lc.get('T1') is None:
        return 'T1'
    if lc.get('T3') is None:
        return 'T3'
    if lc.get('T10') is None:
        return 'T10'
    return 'T10'  # all filled, overwrite last


def update_review_status(state_dir: Path, status: str, human_feedback: str | None = None) -> dict:
    response_path = state_dir / 'ai_decision_response.json'
    ledger_path = state_dir / 'ai_decision_review.jsonl'
    provenance_path = state_dir / 'decision_provenance.jsonl'
    payload = _load_json(response_path)
    reviewed_at = datetime.now(TW_TZ).isoformat()
    payload.setdefault('review', {})
    payload['review']['status'] = status
    payload['review']['reviewed_at'] = reviewed_at
    payload['review']['human_feedback'] = human_feedback
    response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    _append_jsonl(ledger_path, {
        'request_id': payload.get('request_id'),
        'status': status,
        'human_feedback': human_feedback,
        'reviewed_at': reviewed_at,
        'source': payload.get('source'),
    })

    # --- Provenance: update review lifecycle ---
    try:
        request_id = payload.get('request_id', '')
        if request_id:
            window = _determine_review_window(state_dir, request_id)
            update_review_lifecycle(provenance_path, request_id, window, {
                'reviewed_at': reviewed_at,
                'status': status,
                'human_feedback': human_feedback,
                'window': window,
            })
    except Exception as e:
        import warnings
        warnings.warn(f"[provenance] Failed to update review lifecycle: {e}")

    return payload
