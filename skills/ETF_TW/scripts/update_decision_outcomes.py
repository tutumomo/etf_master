#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from etf_core.state_io import safe_load_json, safe_load_jsonl, safe_append_jsonl, atomic_save_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from scripts.etf_core import context
from provenance_logger import finalize_outcome

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
DECISION_OUTCOMES_PATH = STATE / 'decision_outcomes.jsonl'
MARKET_CACHE_PATH = STATE / 'market_cache.json'
PORTFOLIO_SNAPSHOT_PATH = STATE / 'portfolio_snapshot.json'
OUTCOME_SUMMARY_PATH = STATE / 'decision_outcome_summary.json'
PROVENANCE_PATH = STATE / 'decision_provenance.jsonl'


def classify_outcome(row: dict, market_cache: dict, portfolio_snapshot: dict) -> tuple[str, str, float | None]:
    symbol = row.get('symbol')
    if not symbol:
        return 'insufficient-data', '缺少 symbol，無法回填 outcome', None

    quote = (market_cache.get('quotes') or {}).get(symbol) or {}
    price = float(quote.get('current_price') or 0)
    if price <= 0:
        return 'insufficient-data', f'{symbol} 缺少有效報價，暫無法回填 outcome', None

    reference_price = float(row.get('reference_price') or 0)
    if row.get('action') == 'buy-preview' and reference_price > 0:
        return_pct = round(((price - reference_price) / reference_price) * 100, 2)
        if return_pct >= 1.5:
            return 'win', f'{symbol} 目前報酬 {return_pct:.2f}%，達 win 門檻', return_pct
        if return_pct <= -1.5:
            return 'loss', f'{symbol} 目前報酬 {return_pct:.2f}%，達 loss 門檻', return_pct
        return 'flat', f'{symbol} 目前報酬 {return_pct:.2f}%，屬平盤區間', return_pct

    holdings = {item.get('symbol'): item for item in (portfolio_snapshot.get('holdings') or [])}
    if row.get('action') == 'buy-preview':
        if symbol in holdings:
            return 'observed', f'{symbol} 已在持倉快照中，可持續追蹤後續表現', None
        return 'observed', f'{symbol} 有可用報價 {price:.2f}，已建立觀察 outcome', None

    return 'observed', f'{symbol} 有可用報價 {price:.2f}，目前維持觀察', None


def main() -> int:
    now = datetime.now(TW_TZ)
    market_cache = safe_load_json(MARKET_CACHE_PATH, {'quotes': {}})
    portfolio_snapshot = safe_load_json(PORTFOLIO_SNAPSHOT_PATH, {'holdings': []})
    rows = safe_load_jsonl(DECISION_OUTCOMES_PATH)

    updated_rows = []
    observed = 0
    insufficient = 0
    pending = 0
    wins = 0
    losses = 0
    flats = 0
    changed = 0

    for row in rows:
        original_status = row.get('outcome_status', 'pending')
        new_status, note, return_pct = classify_outcome(row, market_cache, portfolio_snapshot)
        if original_status != new_status or row.get('outcome_note') != note:
            changed += 1
        row['outcome_status'] = new_status
        row['outcome_note'] = note
        row['return_pct'] = return_pct
        row['last_evaluated_at'] = now.isoformat()
        updated_rows.append(row)

        if new_status == 'observed':
            observed += 1
        elif new_status == 'insufficient-data':
            insufficient += 1
        elif new_status == 'win':
            wins += 1
        elif new_status == 'loss':
            losses += 1
        elif new_status == 'flat':
            flats += 1
        else:
            pending += 1

    DECISION_OUTCOMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECISION_OUTCOMES_PATH.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in updated_rows), encoding='utf-8')

    # --- Provenance: finalize outcomes for win/loss/flat decisions ---
    for row in updated_rows:
        decision_id = row.get('decision_id', '')
        new_status = row.get('outcome_status', '')
        if decision_id and new_status in ('win', 'loss', 'flat'):
            try:
                finalize_outcome(PROVENANCE_PATH, decision_id, {
                    'finalized_at': now.isoformat(),
                    'verdict': new_status,
                    'return_pct': row.get('return_pct'),
                    'outcome_note': row.get('outcome_note', ''),
                })
            except Exception as e:
                import warnings
                warnings.warn(f"[provenance] Failed to finalize outcome for {decision_id}: {e}")

    summary = {
        'updated_at': now.isoformat(),
        'total': len(updated_rows),
        'observed': observed,
        'insufficient_data': insufficient,
        'pending': pending,
        'wins': wins,
        'losses': losses,
        'flats': flats,
        'changed': changed,
        'source': 'update_decision_outcomes',
    }
    atomic_save_json(OUTCOME_SUMMARY_PATH, summary)
    print('DECISION_OUTCOMES_UPDATE_OK')
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
