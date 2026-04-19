#!/usr/bin/env python3
"""
sync_decision_reviews.py — 自動 T+N 回填與判定

每天 15:05 盤後執行。掃描 decision_provenance.jsonl 中所有尚未填入的
T1/T3/T10 窗口，拉收盤價、計算報酬率、寫入 verdict，並更新
decision_quality_report.json 的雙鏈統計。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core.state_io import atomic_save_json, safe_load_json, safe_load_jsonl
from etf_core import context
from provenance_logger import update_review_lifecycle, finalize_outcome

TW_TZ = ZoneInfo('Asia/Taipei')
WIN_THRESHOLD = 0.015    # +1.5%
LOSS_THRESHOLD = -0.015  # -1.5%
CACHE_MAX_AGE_HOURS = 6
WINDOWS = {'T1': 1, 'T3': 3, 'T10': 10}


# ---------------------------------------------------------------------------
# Trading-day helpers (weekend exclusion only — no TW holiday calendar yet)
# ---------------------------------------------------------------------------

def trading_days_between(start: date, end: date) -> int:
    """Count trading days (Mon–Fri) from start (exclusive) to end (inclusive)."""
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:   # 0=Mon … 4=Fri
            count += 1
        current += timedelta(days=1)
    return count


def windows_due(created_at_str: str, today: date) -> list[str]:
    """Return list of window names ('T1','T3','T10') whose N trading days have elapsed."""
    try:
        created_dt = datetime.fromisoformat(created_at_str)
    except (ValueError, TypeError):
        return []
    created_date = created_dt.date()
    elapsed = trading_days_between(created_date, today)
    return [name for name, days in WINDOWS.items() if elapsed >= days]


# ---------------------------------------------------------------------------
# Price retrieval
# ---------------------------------------------------------------------------

def _fetch_yfinance_price(symbol: str) -> float | None:
    """Fetch most recent closing price from yfinance. Returns None on failure."""
    try:
        import yfinance as yf
        suffix = '.TWO' if symbol.startswith('006') else '.TW'
        ticker = yf.Ticker(f'{symbol}{suffix}')
        hist = ticker.history(period='5d')
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except Exception:
        return None


def get_closing_price(symbol: str, market_cache: dict) -> tuple[float | None, str]:
    """Return (price, source) where source is 'market_cache', 'yfinance', or 'skip'.

    Priority:
      1. market_cache.json quotes[symbol].current_price if updated_at ≤ 6h ago
      2. yfinance fallback (last 5 trading days)
      3. skip (verdict='skip', try next time)
    """
    quotes = market_cache.get('quotes', {})
    quote = quotes.get(symbol, {})
    price_cache = quote.get('current_price')
    updated_at_str = quote.get('updated_at', '')

    if price_cache and updated_at_str:
        try:
            updated_at = datetime.fromisoformat(updated_at_str)
            # Normalize to aware datetime for comparison
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=TW_TZ)
            age_hours = (datetime.now(TW_TZ) - updated_at).total_seconds() / 3600
            if age_hours <= CACHE_MAX_AGE_HOURS:
                return float(price_cache), 'market_cache'
        except (ValueError, TypeError):
            pass

    # Fallback to yfinance
    yf_price = _fetch_yfinance_price(symbol)
    if yf_price is not None:
        return yf_price, 'yfinance'

    return None, 'skip'


# ---------------------------------------------------------------------------
# Verdict + outcome
# ---------------------------------------------------------------------------

def determine_verdict(return_pct: float) -> str:
    """Classify return_pct as win/loss/flat using ±1.5% thresholds."""
    if return_pct >= WIN_THRESHOLD:
        return 'win'
    if return_pct <= LOSS_THRESHOLD:
        return 'loss'
    return 'flat'


def compute_outcome_final(t1: dict, t3: dict, t10: dict) -> dict:
    """Compute outcome_final when all three windows are filled.

    Verdict = majority vote. Tiebreak: t10 wins (longest horizon).
    """
    verdicts = [t1['verdict'], t3['verdict'], t10['verdict']]
    counts = Counter(v for v in verdicts if v not in ('skip',))
    if counts:
        majority = counts.most_common(1)[0][0]
        # On tie (all different), use t10
        if len(counts) == 3:
            majority = t10['verdict']
    else:
        majority = 'skip'

    returns = [t1['return_pct'], t3['return_pct'], t10['return_pct']]
    valid_returns = [r for r in returns if r is not None]

    return {
        'finalized_at': datetime.now(TW_TZ).isoformat(),
        'verdict': majority,
        'max_return_pct': max(valid_returns) if valid_returns else None,
        'min_return_pct': min(valid_returns) if valid_returns else None,
        't1_verdict': t1['verdict'],
        't3_verdict': t3['verdict'],
        't10_verdict': t10['verdict'],
    }


# ---------------------------------------------------------------------------
# Chain breakdown stats
# ---------------------------------------------------------------------------

def _safe_win_rate(bucket: dict) -> float | None:
    total = bucket.get('total', 0)
    if total == 0:
        return None
    wins = bucket.get('win', 0)
    return round(wins / total, 4)


def update_chain_breakdown(records: list[dict], existing_report: dict) -> dict:
    """Recompute chain_breakdown from all records with outcome_final != null."""
    buckets: dict[str, dict] = {
        'rule_engine': {'total': 0, 'win': 0, 'loss': 0, 'flat': 0, 'skip': 0},
        'ai_bridge':   {'total': 0, 'win': 0, 'loss': 0, 'flat': 0, 'skip': 0},
        'tier1_consensus': {'total': 0, 'win': 0, 'loss': 0, 'flat': 0, 'skip': 0},
        'unknown_source':  {'total': 0, 'win': 0, 'loss': 0, 'flat': 0, 'skip': 0},
    }
    total_with_outcome = 0
    total_pending = 0

    for rec in records:
        outcome = rec.get('outcome_final')
        if outcome is None:
            total_pending += 1
            continue

        total_with_outcome += 1
        verdict = outcome.get('verdict', 'skip')
        cs = rec.get('chain_sources')

        if cs is None:
            b = buckets['unknown_source']
            b['total'] += 1
            b[verdict] = b.get(verdict, 0) + 1
            continue

        rule_action = cs.get('rule_engine_action')
        ai_action = cs.get('ai_bridge_action')
        tier = cs.get('consensus_tier')

        # Rule engine bucket: count only when rule engine had an actionable call
        if rule_action and rule_action not in ('hold', None):
            b = buckets['rule_engine']
            b['total'] += 1
            b[verdict] = b.get(verdict, 0) + 1

        # AI bridge bucket: count only when AI had an actionable call
        if ai_action and ai_action.replace('preview_', '') not in ('hold', '', None):
            b = buckets['ai_bridge']
            b['total'] += 1
            b[verdict] = b.get(verdict, 0) + 1

        # Tier 1 consensus bucket
        if tier == 1:
            b = buckets['tier1_consensus']
            b['total'] += 1
            b[verdict] = b.get(verdict, 0) + 1

        # If chain_sources present but neither rule nor AI was actionable → unknown
        rule_was_hold = not rule_action or rule_action == 'hold'
        ai_was_hold = not ai_action or ai_action.replace('preview_', '') in ('hold', '')
        if rule_was_hold and ai_was_hold:
            b = buckets['unknown_source']
            b['total'] += 1
            b[verdict] = b.get(verdict, 0) + 1

    # Add win_rate to each bucket
    for b in buckets.values():
        b['win_rate'] = _safe_win_rate(b)

    report = dict(existing_report)
    report['chain_breakdown'] = buckets
    report['last_updated'] = datetime.now(TW_TZ).isoformat()
    report['total_decisions_with_outcome'] = total_with_outcome
    report['total_pending'] = total_pending
    return report


# ---------------------------------------------------------------------------
# Main backfill loop
# ---------------------------------------------------------------------------

def run_backfill(provenance_path: Path, market_cache: dict, quality_report_path: Path) -> dict:
    """Run T+N backfill on all provenance records. Returns stats dict."""
    today = datetime.now(TW_TZ).date()
    rows = safe_load_jsonl(provenance_path)

    stats = {'processed': 0, 'filled': 0, 'skipped': 0, 'finalized': 0, 'errors': 0}

    for rec in rows:
        decision_id = rec.get('decision_id')
        symbol = (rec.get('outputs') or {}).get('symbol')
        reference_price = (rec.get('outputs') or {}).get('reference_price')
        created_at = rec.get('created_at', '')
        lifecycle = rec.get('review_lifecycle', {})

        if not symbol or not reference_price:
            continue

        stats['processed'] += 1
        due = windows_due(created_at, today)

        for window in due:
            if lifecycle.get(window) is not None:
                continue   # already filled

            price, source = get_closing_price(symbol, market_cache)

            if price is None:
                review_data = {
                    'reviewed_at': datetime.now(TW_TZ).isoformat(),
                    'price_then': None,
                    'reference_price': reference_price,
                    'return_pct': None,
                    'verdict': 'skip',
                    'source': 'skip',
                }
                stats['skipped'] += 1
            else:
                return_pct = (price - reference_price) / reference_price
                verdict = determine_verdict(return_pct)
                review_data = {
                    'reviewed_at': datetime.now(TW_TZ).isoformat(),
                    'price_then': round(price, 4),
                    'reference_price': reference_price,
                    'return_pct': round(return_pct, 6),
                    'verdict': verdict,
                    'source': source,
                }
                stats['filled'] += 1

            update_review_lifecycle(provenance_path, decision_id, window, review_data)

    # Re-read after all updates; check for records ready to finalize
    rows = safe_load_jsonl(provenance_path)
    for rec in rows:
        if rec.get('outcome_final') is not None:
            continue
        lc = rec.get('review_lifecycle', {})
        t1 = lc.get('T1')
        t3 = lc.get('T3')
        t10 = lc.get('T10')
        if t1 is not None and t3 is not None and t10 is not None:
            outcome = compute_outcome_final(t1, t3, t10)
            finalize_outcome(provenance_path, rec['decision_id'], outcome)
            stats['finalized'] += 1

    # Recompute chain_breakdown in quality report
    rows = safe_load_jsonl(provenance_path)
    existing_report = safe_load_json(quality_report_path, {})
    updated_report = update_chain_breakdown(rows, existing_report)
    atomic_save_json(quality_report_path, updated_report)

    return stats


def main() -> int:
    STATE = context.get_state_dir()
    provenance_path = STATE / 'decision_provenance.jsonl'
    quality_report_path = STATE / 'decision_quality_report.json'
    market_cache_path = STATE / 'market_cache.json'

    if not provenance_path.exists():
        print('SYNC_DECISION_REVIEWS_OK:NO_PROVENANCE')
        return 0

    market_cache = safe_load_json(market_cache_path, {'quotes': {}})
    stats = run_backfill(provenance_path, market_cache, quality_report_path)

    print(f"SYNC_DECISION_REVIEWS_OK:"
          f"processed={stats['processed']} "
          f"filled={stats['filled']} "
          f"skipped={stats['skipped']} "
          f"finalized={stats['finalized']} "
          f"errors={stats['errors']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())