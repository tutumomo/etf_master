#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


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


def record_outcome(state_dir: Path, outcome_status: str, outcome_note: str, human_feedback: str | None = None, review_window: str | None = None, review_window_label: str | None = None, offset_trading_days: int | None = None) -> dict:
    response_path = state_dir / 'ai_decision_response.json'
    ledger_path = state_dir / 'ai_decision_outcome.jsonl'
    payload = _load_json(response_path)
    row = {
        'request_id': payload.get('request_id'),
        'recorded_at': datetime.now().astimezone().isoformat(),
        'source': payload.get('source'),
        'symbol': (payload.get('candidate') or {}).get('symbol'),
        'action': (payload.get('decision') or {}).get('action'),
        'summary': (payload.get('decision') or {}).get('summary'),
        'outcome_status': outcome_status,
        'outcome_note': outcome_note,
        'human_feedback': human_feedback,
        'review_window': review_window,
        'review_window_label': review_window_label,
        'offset_trading_days': offset_trading_days,
    }
    _append_jsonl(ledger_path, row)
    return row
