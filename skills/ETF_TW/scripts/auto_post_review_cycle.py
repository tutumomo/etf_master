#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from ai_outcome_lifecycle import record_outcome
from ai_auto_reflection import auto_reflect_if_ready
from layered_review_windows import get_layered_review_windows


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def _write_review_artifact(
    state_dir: Path,
    request_id: str,
    review_window_name: str,
    review_window_label: str | None,
    outcome: dict,
    reflection: dict | None,
    symbol: str | None,
    reference_price,
    current_price,
) -> dict:
    """Write a canonical review artifact for dashboard/agents to consume."""
    base = state_dir / 'layered_review_reviews' / request_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f'{review_window_name}.json'
    artifact = {
        'request_id': request_id,
        'review_window': review_window_name,
        'review_window_label': review_window_label,
        'updated_at': outcome.get('updated_at') or outcome.get('timestamp'),
        'outcome': outcome,
        'reflection': reflection,
        'candidate': {
            'symbol': symbol,
            'reference_price': reference_price,
            'current_price': current_price,
        },
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # index.json for quick summary
    index_path = base / 'index.json'
    index = _load_json(index_path) or {}
    windows = index.get('windows') or {}
    windows[review_window_name] = {
        'path': str(path),
        'updated_at': artifact.get('updated_at'),
        'review_window_label': review_window_label,
        'outcome_status': outcome.get('outcome_status') or outcome.get('status'),
        'outcome_note': outcome.get('outcome_note') or outcome.get('note'),
    }
    index['request_id'] = request_id
    index['updated_at'] = artifact.get('updated_at')
    index['windows'] = windows
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    return {'artifact_path': str(path), 'index_path': str(index_path)}


def run_auto_post_review_cycle(
    state_dir: Path,
    outcome_note: str = '隔日自動復盤',
    review_window: str = 'early_review',
    request_id: str | None = None,
) -> dict:
    response = _load_json(state_dir / 'ai_decision_response.json')
    derived_request_id = response.get('request_id')
    request_id = request_id or derived_request_id
    if not request_id:
        return {'skipped': True, 'reason': 'missing_request_id'}

    review = response.get('review') or {}
    if review.get('status') not in {'reviewed', 'superseded'}:
        response.setdefault('review', {})
        response['review']['status'] = 'reviewed'
        response['review'].setdefault('human_feedback', 'auto-post-review-cycle')
        (state_dir / 'ai_decision_response.json').write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')

    candidate = response.get('candidate') or {}
    symbol = candidate.get('symbol')
    ref_price = candidate.get('reference_price')
    market_cache = _load_json(state_dir / 'market_cache.json')
    current_price = (((market_cache.get('quotes') or {}).get(symbol) or {}).get('current_price')) if symbol else None

    windows = {w['name']: w for w in get_layered_review_windows()}
    review_window_payload = windows.get(review_window, windows['early_review'])
    final_outcome_note = f"{review_window_payload['label']}｜{outcome_note}"
    final_outcome_status = 'tracked'
    if symbol and ref_price not in (None, 0, 0.0) and current_price not in (None, 0, 0.0):
        try:
            delta = float(current_price) - float(ref_price)
            pct = (delta / float(ref_price)) * 100 if float(ref_price) else 0.0
            direction = '上升' if delta >= 0 else '下跌'
            final_outcome_note = f"{review_window_payload['label']}｜{symbol} 較建議參考價{direction} {abs(delta):.2f}（{abs(pct):.2f}%）"
            final_outcome_status = 'reviewed'
        except Exception:
            pass

    outcome = record_outcome(
        state_dir,
        outcome_status=final_outcome_status,
        outcome_note=final_outcome_note,
        human_feedback='auto-post-review-cycle',
        review_window=review_window_payload.get('name'),
        review_window_label=review_window_payload.get('label'),
        offset_trading_days=review_window_payload.get('offset_trading_days'),
    )
    reflection = auto_reflect_if_ready(state_dir)

    artifact = _write_review_artifact(
        state_dir=state_dir,
        request_id=request_id,
        review_window_name=review_window_payload.get('name') or review_window,
        review_window_label=review_window_payload.get('label'),
        outcome=outcome or {},
        reflection=reflection if isinstance(reflection, dict) else None,
        symbol=symbol,
        reference_price=ref_price,
        current_price=current_price,
    )

    return {
        'skipped': False,
        'request_id': request_id,
        'review_window': review_window_payload,
        'outcome': outcome,
        'reflection': reflection,
        'artifact': artifact,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('state_dir', nargs='?', default=str(ROOT / 'instances' / 'etf_master' / 'state'))
    parser.add_argument('--request-id', default=None)
    parser.add_argument('--review-window', default='early_review')
    parser.add_argument('--outcome-note', default='隔日自動復盤')
    args = parser.parse_args()

    target_dir = Path(args.state_dir)
    result = run_auto_post_review_cycle(
        target_dir,
        outcome_note=args.outcome_note,
        review_window=args.review_window,
        request_id=args.request_id,
    )
    print(json.dumps(result, ensure_ascii=False))
