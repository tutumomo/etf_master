#!/usr/bin/env python3
"""
Decision Provenance Logger — append-only, atomic record of every decision cycle.

Design Principles:
  1. Append-only: never overwrite, never delete (audit trail)
  2. One record per decision: inputs + outputs + review lifecycle in a single JSONL line
  3. Compressed inputs: only decision-relevant summaries, NOT raw market_cache dumps
  4. Review back-fill: T+1/T+3/T+10 update the same record via decision_id lookup
  5. No paper/live confusion: provenance records observations, NOT trades

Schema (v1):
  {
    "provenance_version": 1,
    "decision_id": "decision-20260411T224500-a1b2c3d4",
    "created_at": "2026-04-11T22:45:00+08:00",
    "source": "run_auto_decision_scan" | "generate_ai_decision_response" | "agent_manual",
    "strategy_snapshot": {
      "base_strategy": "收益優先",
      "scenario_overlay": "高波動警戒"
    },
    "inputs_digest": {
      "position_symbols": ["0050", "00878"],
      "total_equity": 31631.75,
      "cash": 8900.0,
      "open_orders_count": 1,
      "market_regime": "cautious",
      "risk_temperature": "elevated",
      "global_risk_level": "elevated",
      "defensive_bias": "high",
      "tape_bias": "bullish",
      "top_risks": ["中東地緣政治風險持續", "能源價格偏高"]
    },
    "outputs": {
      "action": "preview_buy" | "hold",
      "symbol": "00679B" | null,
      "reference_price": 27.23 | null,
      "quantity": 100 | null,
      "confidence": "medium" | "high" | "low",
      "score": 6,
      "summary": "建議優先觀察 00679B...",
      "top_candidate_reasons": ["屬於防守配置池", "..."],
      "risk_notes": ["目前市場風險溫度偏高..."],
      "all_candidates_top3": [...]  // compact: symbol, score, group only
    },
    "review_lifecycle": {
      "T1": null,           // {"reviewed_at": "...", "price_then": X, "return_pct": Y, "verdict": "win|loss|flat|observed|skip"}
      "T3": null,
      "T10": null
    },
    "outcome_final": null,   // {"finalized_at": "...", "verdict": "win|loss|flat|observed", "max_return_pct": X}
    "tags": []               // e.g. ["first_00679B_recommendation", "risk_elevated"]
  }
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from etf_core.state_io import safe_append_jsonl, safe_load_jsonl

TW_TZ = ZoneInfo('Asia/Taipei')
PROVENANCE_VERSION = 1


def _now_iso() -> str:
    return datetime.now(TW_TZ).isoformat()


def compress_inputs(request_payload: dict) -> dict:
    """Extract decision-relevant summary from a full ai_decision_request payload."""
    inputs = request_payload.get('inputs', {})

    # Position digest
    positions = inputs.get('positions', {})
    pos_list = positions.get('positions', [])
    position_symbols = [p.get('symbol') for p in pos_list if p.get('symbol')]

    # Portfolio digest
    snapshot = inputs.get('portfolio_snapshot', {})
    total_equity = snapshot.get('total_equity')
    cash = snapshot.get('cash')

    # Orders digest
    orders = inputs.get('orders_open', {})
    open_orders = orders.get('orders', [])
    open_orders_count = len(open_orders)

    # Market context digest
    mc = inputs.get('market_context_taiwan', {})
    event_ctx = inputs.get('market_event_context', {})
    tape_ctx = inputs.get('intraday_tape_context', {})

    # Strategy digest
    strategy = inputs.get('strategy', {})

    return {
        'position_symbols': position_symbols,
        'total_equity': total_equity,
        'cash': cash,
        'open_orders_count': open_orders_count,
        'market_regime': mc.get('market_regime', 'unknown'),
        'risk_temperature': mc.get('risk_temperature', 'unknown'),
        'global_risk_level': event_ctx.get('global_risk_level', 'unknown'),
        'defensive_bias': event_ctx.get('defensive_bias', mc.get('defensive_tilt', 'unknown')),
        'tape_bias': tape_ctx.get('market_bias', 'unknown'),
        'top_risks': mc.get('top_risks', []),
        'base_strategy': strategy.get('base_strategy', 'unknown'),
        'scenario_overlay': strategy.get('scenario_overlay', 'unknown'),
    }


def compress_outputs(response_payload: dict, scan_result: dict | None = None) -> dict:
    """Extract decision-relevant summary from response + optional scan result."""
    decision = response_payload.get('decision', {})
    candidate = response_payload.get('candidate', {})

    top3 = []
    if scan_result and scan_result.get('top_candidates'):
        for c in scan_result['top_candidates'][:3]:
            top3.append({
                'symbol': c.get('symbol'),
                'score': c.get('score'),
                'group': c.get('group'),
            })

    return {
        'action': decision.get('action'),
        'symbol': candidate.get('symbol') or None,
        'reference_price': candidate.get('reference_price'),
        'quantity': candidate.get('quantity'),
        'confidence': decision.get('confidence', 'unknown'),
        'score': scan_result.get('candidate', {}).get('score') if scan_result else None,
        'summary': decision.get('summary', ''),
        'top_candidate_reasons': scan_result.get('candidate', {}).get('reasons', []) if scan_result else [],
        'risk_notes': scan_result.get('candidate', {}).get('risk_notes', []) if scan_result else [],
        'all_candidates_top3': top3,
    }


def build_provenance_record(
    *,
    request_payload: dict,
    response_payload: dict,
    scan_result: dict | None = None,
    source: str = 'unknown',
    tags: list[str] | None = None,
    chain_sources: dict | None = None,
) -> dict:
    """Build a complete provenance record from request + response + optional scan context.

    Args:
        chain_sources: Dual-chain arbitration metadata from resolve_consensus().
            Contains rule_engine_action, ai_bridge_action, consensus_tier, etc.
    """
    strategy_snap = compress_inputs(request_payload)
    record = {
        'provenance_version': PROVENANCE_VERSION,
        'decision_id': response_payload.get('request_id', f"decision-{datetime.now(TW_TZ).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}"),
        'created_at': _now_iso(),
        'source': source,
        'strategy_snapshot': {
            'base_strategy': strategy_snap.get('base_strategy', 'unknown'),
            'scenario_overlay': strategy_snap.get('scenario_overlay', 'unknown'),
        },
        'inputs_digest': strategy_snap,
        'outputs': compress_outputs(response_payload, scan_result),
        'chain_sources': chain_sources,
        'review_lifecycle': {
            'T1': None,
            'T3': None,
            'T10': None,
        },
        'outcome_final': None,
        'tags': tags or [],
    }
    return record


def append_provenance(provenance_path: Path, record: dict) -> Path:
    """Append a provenance record to the JSONL file."""
    return safe_append_jsonl(provenance_path, record)


def find_provenance_by_decision_id(provenance_path: Path, decision_id: str) -> dict | None:
    """Find a provenance record by decision_id. Returns the record or None."""
    rows = safe_load_jsonl(provenance_path)
    for row in reversed(rows):  # search from newest
        if row.get('decision_id') == decision_id:
            return row
    return None


def update_review_lifecycle(
    provenance_path: Path,
    decision_id: str,
    review_window: str,  # "T1" | "T3" | "T10"
    review_data: dict,
) -> bool:
    """Update a specific review slot in a provenance record.

    Since JSONL is append-only, this rewrites the entire file with the update.
    This is acceptable for provenance files (relatively small, <10k lines expected).
    """
    rows = safe_load_jsonl(provenance_path)
    found = False
    for row in rows:
        if row.get('decision_id') == decision_id:
            lifecycle = row.get('review_lifecycle', {})
            lifecycle[review_window] = review_data
            row['review_lifecycle'] = lifecycle
            found = True
            break

    if not found:
        return False

    # Rewrite entire file
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows),
        encoding='utf-8',
    )
    return True


def finalize_outcome(
    provenance_path: Path,
    decision_id: str,
    outcome_data: dict,
) -> bool:
    """Set the outcome_final field on a provenance record."""
    rows = safe_load_jsonl(provenance_path)
    found = False
    for row in rows:
        if row.get('decision_id') == decision_id:
            row['outcome_final'] = outcome_data
            found = True
            break

    if not found:
        return False

    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows),
        encoding='utf-8',
    )
    return True


def provenance_summary(provenance_path: Path, limit: int = 5) -> dict:
    """Quick summary of recent provenance records for dashboard / memory context."""
    rows = safe_load_jsonl(provenance_path)
    total = len(rows)
    recent = rows[-limit:] if total > limit else rows

    pending_reviews = 0
    completed_reviews = 0
    for row in recent:
        lc = row.get('review_lifecycle', {})
        if lc.get('T1') is None:
            pending_reviews += 1
        else:
            completed_reviews += 1

    recent_digests = []
    for row in recent:
        outputs = row.get('outputs', {})
        recent_digests.append({
            'decision_id': row.get('decision_id'),
            'created_at': row.get('created_at'),
            'action': outputs.get('action'),
            'symbol': outputs.get('symbol'),
            'confidence': outputs.get('confidence'),
            'score': outputs.get('score'),
            'outcome_final': row.get('outcome_final'),
            'review_T1': row.get('review_lifecycle', {}).get('T1') is not None,
        })

    return {
        'total_records': total,
        'pending_reviews': pending_reviews,
        'completed_reviews': completed_reviews,
        'recent': recent_digests,
    }