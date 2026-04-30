# Auto Decision Review Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully automate the T+N price backfill → verdict → dual-chain win-rate stats → weekly wiki report cycle, eliminating all manual `reviewed`/`superseded` labeling steps.

**Architecture:** Three sub-systems wired together: (1) `sync_decision_reviews.py` runs at 15:05 weekdays to backfill T1/T3/T10 verdict windows via `market_cache` → yfinance fallback; (2) `decision_quality_report.json` is extended with a `chain_breakdown` block tracking rule_engine/ai_bridge/tier1 win rates; (3) `generate_decision_quality_weekly.py` runs at 09:05 Saturday to write a wiki report at a stable path for AI Bridge context injection.

**Tech Stack:** Python 3.14+, `yfinance`, `provenance_logger.py` (existing), `state_io.py` (existing), cron/jobs.json (existing)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/provenance_logger.py` | Modify | Accept `chain_sources` param in `build_provenance_record()` |
| `scripts/run_auto_decision_scan.py` | Modify | Pass `consensus` dict to `build_provenance_record()` |
| `scripts/sync_decision_reviews.py` | Create | T+N backfill cron script (15:05 daily) |
| `scripts/generate_decision_quality_weekly.py` | Create | Saturday wiki report writer (09:05 Sat) |
| `cron/jobs.json` | Modify | Add 2 new cron jobs |
| `tests/test_sync_decision_reviews.py` | Create | Unit tests for backfill logic |
| `tests/test_generate_decision_quality_weekly.py` | Create | Unit tests for weekly report |

---

## Task 1: Add `chain_sources` to `build_provenance_record()`

**Files:**
- Modify: `scripts/provenance_logger.py:145-174`
- Modify: `scripts/run_auto_decision_scan.py:880-887`
- Test: `tests/test_sync_decision_reviews.py` (scaffold)

### Background

`build_provenance_record()` in `provenance_logger.py:145` currently takes `request_payload`, `response_payload`, `scan_result`, `source`, `tags`. We add an optional `chain_sources` parameter.

In `run_auto_decision_scan.py:880-887`, `build_provenance_record()` is called after the `consensus` dict is built at line 754. We need to extract `chain_sources` from `consensus` and pass it.

- [ ] **Step 1: Write the failing test scaffold**

Create `skills/ETF_TW/tests/test_sync_decision_reviews.py`:

```python
"""Tests for sync_decision_reviews.py and provenance chain_sources field."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def test_build_provenance_record_includes_chain_sources():
    """build_provenance_record() must store chain_sources when provided."""
    from provenance_logger import build_provenance_record

    request_payload = {
        'request_id': 'test-001',
        'inputs': {
            'strategy': {'base_strategy': '平衡配置', 'scenario_overlay': '無'},
            'positions': {'holdings': [], 'positions': []},
            'market_context_taiwan': {'market_regime': 'neutral', 'risk_temperature': 'normal'},
            'market_event_context': {'global_risk_level': 'low', 'defensive_bias': 'low'},
            'intraday_tape_context': {'market_bias': 'neutral'},
            'portfolio_snapshot': {'total_equity': 10000.0, 'cash': 5000.0},
            'orders_open': {'orders': []},
        }
    }
    response_payload = {
        'request_id': 'test-001',
        'decision': {'action': 'buy-preview', 'confidence': 'high', 'summary': 'test'},
        'candidate': {'symbol': '00878', 'reference_price': 20.5, 'quantity': 100},
    }
    chain_sources = {
        'rule_engine_action': 'buy',
        'rule_engine_symbol': '00878',
        'ai_bridge_action': 'preview_buy',
        'ai_bridge_symbol': '00878',
        'consensus_tier': 1,
        'consensus_resolved': 'buy',
        'strategy_aligned_rule': True,
        'strategy_aligned_ai': True,
    }

    record = build_provenance_record(
        request_payload=request_payload,
        response_payload=response_payload,
        source='test',
        chain_sources=chain_sources,
    )

    assert 'chain_sources' in record
    assert record['chain_sources']['consensus_tier'] == 1
    assert record['chain_sources']['rule_engine_symbol'] == '00878'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sync_decision_reviews.py::test_build_provenance_record_includes_chain_sources -v
```

Expected: FAIL with `TypeError: build_provenance_record() got an unexpected keyword argument 'chain_sources'`

- [ ] **Step 3: Add `chain_sources` param to `build_provenance_record()`**

In `scripts/provenance_logger.py`, change the function signature at line 145 and add `chain_sources` to the returned record:

```python
def build_provenance_record(
    *,
    request_payload: dict,
    response_payload: dict,
    scan_result: dict | None = None,
    source: str = 'unknown',
    tags: list[str] | None = None,
    chain_sources: dict | None = None,
) -> dict:
    """Build a complete provenance record from request + response + optional scan context."""
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sync_decision_reviews.py::test_build_provenance_record_includes_chain_sources -v
```

Expected: PASS

- [ ] **Step 5: Update `run_auto_decision_scan.py` to pass `chain_sources`**

In `scripts/run_auto_decision_scan.py`, find the `build_provenance_record()` call at line ~881 and add `chain_sources`:

```python
        # Build chain_sources from consensus dict
        chain_sources_payload = {
            'rule_engine_action': consensus.get('rule_engine'),
            'rule_engine_symbol': consensus.get('rule_engine_symbol'),
            'ai_bridge_action': consensus.get('ai_bridge'),
            'ai_bridge_symbol': consensus.get('ai_bridge_symbol'),
            'consensus_tier': consensus.get('tier'),
            'consensus_resolved': consensus.get('resolved'),
            'strategy_aligned_rule': (consensus.get('strategy_alignment_signal') or {}).get('rule'),
            'strategy_aligned_ai': (consensus.get('strategy_alignment_signal') or {}).get('ai'),
        }
        record = build_provenance_record(
            request_payload=request_payload,
            response_payload=response_payload,
            scan_result=scan_result,
            source='run_auto_decision_scan',
            chain_sources=chain_sources_payload,
        )
```

The full block around line 881 should look like:

```python
        scan_result = result
        # Build chain_sources from consensus dict
        chain_sources_payload = {
            'rule_engine_action': consensus.get('rule_engine'),
            'rule_engine_symbol': consensus.get('rule_engine_symbol'),
            'ai_bridge_action': consensus.get('ai_bridge'),
            'ai_bridge_symbol': consensus.get('ai_bridge_symbol'),
            'consensus_tier': consensus.get('tier'),
            'consensus_resolved': consensus.get('resolved'),
            'strategy_aligned_rule': (consensus.get('strategy_alignment_signal') or {}).get('rule'),
            'strategy_aligned_ai': (consensus.get('strategy_alignment_signal') or {}).get('ai'),
        }
        record = build_provenance_record(
            request_payload=request_payload,
            response_payload=response_payload,
            scan_result=scan_result,
            source='run_auto_decision_scan',
            chain_sources=chain_sources_payload,
        )
```

- [ ] **Step 6: Run full test suite to verify no regressions**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -10
```

Expected: Same passed count as before (353+), 0 failures.

- [ ] **Step 7: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/provenance_logger.py \
        skills/ETF_TW/scripts/run_auto_decision_scan.py \
        skills/ETF_TW/tests/test_sync_decision_reviews.py
git commit -m "feat(provenance): add chain_sources field to build_provenance_record()"
```

---

## Task 2: Create `sync_decision_reviews.py` — T+N backfill

**Files:**
- Create: `scripts/sync_decision_reviews.py`
- Test: `tests/test_sync_decision_reviews.py` (extend)

### Background

This script runs at 15:05 weekdays. It scans `decision_provenance.jsonl` for records where T1/T3/T10 windows are due but not yet filled, fetches the closing price (from `market_cache` if fresh, else yfinance), computes `return_pct`, assigns verdict (`win`/`loss`/`flat`/`skip`), and writes back via `update_review_lifecycle()`. When all three windows are filled, it writes `outcome_final` via `finalize_outcome()`. Then it recomputes `decision_quality_report.json` with a `chain_breakdown` block.

Trading-day counting: exclude weekends only (no Taiwan holiday calendar for now, per spec).

**Verdict thresholds:** `WIN_THRESHOLD = +0.015`, `LOSS_THRESHOLD = -0.015`.

- [ ] **Step 1: Write all backfill tests**

Add to `tests/test_sync_decision_reviews.py`:

```python
def test_trading_days_between_excludes_weekends():
    """Count of trading days between two dates excludes Sat/Sun."""
    from sync_decision_reviews import trading_days_between
    from datetime import date

    # Mon 2026-04-13 → Tue 2026-04-14 = 1 trading day
    assert trading_days_between(date(2026, 4, 13), date(2026, 4, 14)) == 1

    # Fri 2026-04-17 → Mon 2026-04-20 = 1 trading day (weekend skipped)
    assert trading_days_between(date(2026, 4, 17), date(2026, 4, 20)) == 1

    # Mon 2026-04-13 → Fri 2026-04-17 = 4 trading days
    assert trading_days_between(date(2026, 4, 13), date(2026, 4, 17)) == 4


def test_determine_verdict():
    """Verdict thresholds: +1.5% = win, -1.5% = loss, between = flat."""
    from sync_decision_reviews import determine_verdict

    assert determine_verdict(0.02) == 'win'
    assert determine_verdict(0.015) == 'win'
    assert determine_verdict(0.014) == 'flat'
    assert determine_verdict(0.0) == 'flat'
    assert determine_verdict(-0.014) == 'flat'
    assert determine_verdict(-0.015) == 'loss'
    assert determine_verdict(-0.02) == 'loss'


def test_get_closing_price_from_cache():
    """get_closing_price() returns cache price when updated_at is within 6 hours."""
    from sync_decision_reviews import get_closing_price
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    TW_TZ = ZoneInfo('Asia/Taipei')
    fresh_ts = (datetime.now(TW_TZ) - timedelta(hours=1)).isoformat()

    market_cache = {
        'quotes': {
            '00878': {
                'current_price': 22.5,
                'updated_at': fresh_ts,
            }
        }
    }

    price, source = get_closing_price('00878', market_cache)
    assert price == 22.5
    assert source == 'market_cache'


def test_get_closing_price_stale_cache_returns_none():
    """get_closing_price() skips stale cache (>6 hours old)."""
    from sync_decision_reviews import get_closing_price
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    TW_TZ = ZoneInfo('Asia/Taipei')
    stale_ts = (datetime.now(TW_TZ) - timedelta(hours=8)).isoformat()

    market_cache = {
        'quotes': {
            '00878': {
                'current_price': 22.5,
                'updated_at': stale_ts,
            }
        }
    }

    with patch('sync_decision_reviews._fetch_yfinance_price', return_value=None):
        price, source = get_closing_price('00878', market_cache)

    assert price is None
    assert source == 'skip'


def test_compute_outcome_final_majority_verdict():
    """outcome_final verdict is the majority verdict from T1/T3/T10."""
    from sync_decision_reviews import compute_outcome_final

    t1 = {'return_pct': 1.8, 'verdict': 'win'}
    t3 = {'return_pct': 2.1, 'verdict': 'win'}
    t10 = {'return_pct': -1.6, 'verdict': 'loss'}

    outcome = compute_outcome_final(t1, t3, t10)

    assert outcome['verdict'] == 'win'          # 2 win vs 1 loss
    assert outcome['max_return_pct'] == 2.1
    assert outcome['min_return_pct'] == -1.6
    assert outcome['t1_verdict'] == 'win'
    assert outcome['t3_verdict'] == 'win'
    assert outcome['t10_verdict'] == 'loss'
    assert 'finalized_at' in outcome


def test_compute_outcome_final_tie_uses_t10():
    """On a 3-way tie, t10 verdict is preferred (longer horizon wins)."""
    from sync_decision_reviews import compute_outcome_final

    t1 = {'return_pct': 1.8, 'verdict': 'win'}
    t3 = {'return_pct': -0.5, 'verdict': 'flat'}
    t10 = {'return_pct': -1.6, 'verdict': 'loss'}

    outcome = compute_outcome_final(t1, t3, t10)

    assert outcome['verdict'] == 'loss'    # 1 each: tiebreak to t10


def test_update_chain_breakdown():
    """update_chain_breakdown() correctly tallies rule_engine/ai_bridge/tier1 verdicts."""
    from sync_decision_reviews import update_chain_breakdown

    records = [
        {
            'outcome_final': {'verdict': 'win'},
            'chain_sources': {
                'rule_engine_action': 'buy',
                'ai_bridge_action': 'preview_buy',
                'consensus_tier': 1,
            },
        },
        {
            'outcome_final': {'verdict': 'loss'},
            'chain_sources': {
                'rule_engine_action': 'buy',
                'ai_bridge_action': 'hold',
                'consensus_tier': 2,
            },
        },
        {
            'outcome_final': None,       # not yet finalized — should be excluded
            'chain_sources': None,
        },
    ]

    report = {}
    result = update_chain_breakdown(records, report)

    assert result['chain_breakdown']['rule_engine']['total'] == 2
    assert result['chain_breakdown']['rule_engine']['win'] == 1
    assert result['chain_breakdown']['rule_engine']['loss'] == 1
    assert result['chain_breakdown']['ai_bridge']['total'] == 2
    assert result['chain_breakdown']['ai_bridge']['win'] == 1
    assert result['chain_breakdown']['tier1_consensus']['total'] == 1
    assert result['chain_breakdown']['tier1_consensus']['win'] == 1
    assert result['total_decisions_with_outcome'] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sync_decision_reviews.py -v --tb=short 2>&1 | grep -E "FAILED|ERROR|passed|failed"
```

Expected: All new tests FAIL with `ModuleNotFoundError: No module named 'sync_decision_reviews'`

- [ ] **Step 3: Create `scripts/sync_decision_reviews.py`**

Create `skills/ETF_TW/scripts/sync_decision_reviews.py`:

```python
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
    """Return (price, source) where source is 'market_cache', 'yfinance', or 'skip'."""
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
        if ai_action and ai_action.replace('preview_', '') not in ('hold', None, ''):
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
```

- [ ] **Step 4: Run the new tests to verify they pass**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sync_decision_reviews.py -v --tb=short
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

Expected: 360+ passed, 0 failures.

- [ ] **Step 6: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/sync_decision_reviews.py \
        skills/ETF_TW/tests/test_sync_decision_reviews.py
git commit -m "feat(reviews): add sync_decision_reviews.py — automated T+N backfill"
```

---

## Task 3: Create `generate_decision_quality_weekly.py` — Saturday wiki report

**Files:**
- Create: `scripts/generate_decision_quality_weekly.py`
- Test: `tests/test_generate_decision_quality_weekly.py`

### Background

Runs Saturday 09:05. Reads `decision_provenance.jsonl` + `decision_quality_report.json`, computes:
- New decisions this week
- T1/T3/T10 fills this week
- Double-chain win rates (cumulative, from `chain_breakdown`)
- Top 3 wins / Top 3 losses (by return_pct among finalized records this week)
- 4-week trend table

Writes two files:
1. `wiki/decision-weekly-YYYY-WNN.md` (e.g. `wiki/decision-weekly-2026-W17.md`)
2. `wiki/decision-quality-latest.md` (fixed-path symlink for AI Bridge)

- [ ] **Step 1: Write all weekly report tests**

Create `skills/ETF_TW/tests/test_generate_decision_quality_weekly.py`:

```python
"""Tests for generate_decision_quality_weekly.py."""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

TW_TZ = ZoneInfo('Asia/Taipei')


def _make_record(decision_id, created_at, symbol, reference_price, outcome_final=None, chain_sources=None):
    return {
        'decision_id': decision_id,
        'created_at': created_at,
        'outputs': {'symbol': symbol, 'reference_price': reference_price, 'action': 'buy-preview'},
        'review_lifecycle': {'T1': None, 'T3': None, 'T10': None},
        'outcome_final': outcome_final,
        'chain_sources': chain_sources,
    }


def test_iso_week_key():
    """iso_week_key returns YYYY-WNN format."""
    from generate_decision_quality_weekly import iso_week_key
    d = date(2026, 4, 20)   # Monday of week 17
    assert iso_week_key(d) == '2026-W17'


def test_collect_week_stats_new_decisions():
    """collect_week_stats counts new decisions created in the target week."""
    from generate_decision_quality_weekly import collect_week_stats

    records = [
        _make_record('d1', '2026-04-20T09:00:00+08:00', '00878', 20.0),
        _make_record('d2', '2026-04-21T09:00:00+08:00', '0050', 84.0),
        _make_record('d3', '2026-04-07T09:00:00+08:00', '0056', 30.0),  # prior week
    ]

    week = date(2026, 4, 20)   # ISO week 17
    stats = collect_week_stats(records, week)

    assert stats['new_decisions'] == 2
    assert stats['total_decisions'] == 3


def test_collect_week_stats_t1_fills():
    """collect_week_stats counts T1 fills that happened during the target week."""
    from generate_decision_quality_weekly import collect_week_stats

    t1_data = {
        'reviewed_at': '2026-04-21T15:05:00+08:00',
        'price_then': 20.5,
        'reference_price': 20.0,
        'return_pct': 0.025,
        'verdict': 'win',
        'source': 'market_cache',
    }
    record = _make_record('d1', '2026-04-20T09:00:00+08:00', '00878', 20.0)
    record['review_lifecycle']['T1'] = t1_data

    week = date(2026, 4, 20)
    stats = collect_week_stats([record], week)

    assert stats['t1_filled_this_week'] == 1


def test_format_weekly_report_contains_key_sections():
    """format_weekly_report output contains all required markdown sections."""
    from generate_decision_quality_weekly import format_weekly_report

    chain_breakdown = {
        'rule_engine': {'total': 10, 'win': 4, 'loss': 3, 'flat': 3, 'win_rate': 0.4},
        'ai_bridge': {'total': 10, 'win': 6, 'loss': 2, 'flat': 2, 'win_rate': 0.6},
        'tier1_consensus': {'total': 6, 'win': 4, 'loss': 1, 'flat': 1, 'win_rate': 0.667},
        'unknown_source': {'total': 2, 'win': 1, 'loss': 1, 'flat': 0, 'win_rate': 0.5},
    }
    week_stats = {
        'new_decisions': 5,
        'total_decisions': 20,
        't1_filled_this_week': 4,
        't3_filled_this_week': 2,
        't10_filled_this_week': 1,
        'finalized_this_week': 3,
        'top_wins': [{'symbol': '00878', 'window': 'T3', 'return_pct': 2.1, 'verdict': 'win'}],
        'top_losses': [{'symbol': '00679B', 'window': 'T1', 'return_pct': -2.3, 'verdict': 'loss'}],
    }
    week_key = '2026-W17'
    week_date = date(2026, 4, 26)   # Saturday

    report_md = format_weekly_report(week_key, week_date, week_stats, chain_breakdown)

    assert '2026-W17' in report_md
    assert '規則引擎' in report_md
    assert 'AI Bridge' in report_md
    assert 'Tier 1' in report_md
    assert '00878' in report_md
    assert '00679B' in report_md
    assert '## 本週摘要' in report_md
    assert '## 雙鏈勝率' in report_md


def test_write_weekly_report_creates_files(tmp_path):
    """write_weekly_report creates both the dated file and decision-quality-latest.md."""
    from generate_decision_quality_weekly import write_weekly_report

    content = "# Test Report\nSome content"
    week_key = '2026-W17'
    wiki_dir = tmp_path / 'wiki'
    wiki_dir.mkdir()

    paths = write_weekly_report(content, week_key, wiki_dir)

    dated_path = wiki_dir / 'decision-weekly-2026-W17.md'
    latest_path = wiki_dir / 'decision-quality-latest.md'

    assert dated_path.exists()
    assert latest_path.exists()
    assert dated_path.read_text() == content
    assert latest_path.read_text() == content
    assert paths['dated'] == dated_path
    assert paths['latest'] == latest_path
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_decision_quality_weekly.py -v --tb=short 2>&1 | grep -E "FAILED|ERROR|passed|failed"
```

Expected: All 5 tests FAIL with `ModuleNotFoundError: No module named 'generate_decision_quality_weekly'`

- [ ] **Step 3: Create `scripts/generate_decision_quality_weekly.py`**

Create `skills/ETF_TW/scripts/generate_decision_quality_weekly.py`:

```python
#!/usr/bin/env python3
"""
generate_decision_quality_weekly.py — 週報產出腳本

每週六 09:05 執行。讀取 decision_provenance.jsonl + decision_quality_report.json，
計算本週統計與雙鏈勝率，寫入 wiki/decision-weekly-YYYY-WNN.md
並同步更新 wiki/decision-quality-latest.md 供 AI Bridge 引用。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core.state_io import safe_load_json, safe_load_jsonl
from etf_core import context

TW_TZ = ZoneInfo('Asia/Taipei')
WIKI_DIR = Path(__file__).resolve().parents[1] / 'wiki'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iso_week_key(d: date) -> str:
    """Return 'YYYY-WNN' ISO week string for date d."""
    iso_year, iso_week, _ = d.isocalendar()
    return f'{iso_year}-W{iso_week:02d}'


def _date_of_iso_week_start(week_key: str) -> date:
    """Return the Monday of the given ISO week key."""
    year_str, week_str = week_key.split('-W')
    # ISO week 1 of year: find the first Monday
    jan4 = date(int(year_str), 1, 4)
    week_monday = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=int(week_str) - 1)
    return week_monday


def _parse_date(dt_str: str) -> date | None:
    try:
        return datetime.fromisoformat(dt_str).date()
    except (ValueError, TypeError):
        return None


def _in_week(dt_str: str, week_key: str) -> bool:
    """Return True if dt_str falls within the ISO week identified by week_key."""
    d = _parse_date(dt_str)
    if d is None:
        return False
    return iso_week_key(d) == week_key


# ---------------------------------------------------------------------------
# Stats collector
# ---------------------------------------------------------------------------

def collect_week_stats(records: list[dict], week_start: date) -> dict:
    """Aggregate per-week statistics from provenance records."""
    week_key = iso_week_key(week_start)

    new_decisions = 0
    t1_filled = 0
    t3_filled = 0
    t10_filled = 0
    finalized = 0
    top_wins = []
    top_losses = []

    for rec in records:
        created_at = rec.get('created_at', '')
        if _in_week(created_at, week_key):
            new_decisions += 1

        lc = rec.get('review_lifecycle', {})
        for window, counter_ref in (('T1', 't1_filled'), ('T3', 't3_filled'), ('T10', 't10_filled')):
            slot = lc.get(window)
            if slot and _in_week(slot.get('reviewed_at', ''), week_key):
                if window == 'T1':
                    t1_filled += 1
                elif window == 'T3':
                    t3_filled += 1
                elif window == 'T10':
                    t10_filled += 1

        outcome = rec.get('outcome_final')
        if outcome and _in_week(outcome.get('finalized_at', ''), week_key):
            finalized += 1
            symbol = (rec.get('outputs') or {}).get('symbol', '?')
            # Find the window + return that gave the verdict
            for wname in ('T1', 'T3', 'T10'):
                slot = lc.get(wname)
                if slot and slot.get('verdict') == outcome.get('verdict'):
                    ret = slot.get('return_pct', 0) or 0
                    entry = {
                        'symbol': symbol,
                        'window': wname,
                        'return_pct': round(ret * 100, 2),
                        'verdict': outcome.get('verdict'),
                    }
                    if outcome.get('verdict') == 'win':
                        top_wins.append(entry)
                    elif outcome.get('verdict') == 'loss':
                        top_losses.append(entry)
                    break

    top_wins.sort(key=lambda x: x['return_pct'], reverse=True)
    top_losses.sort(key=lambda x: x['return_pct'])

    return {
        'new_decisions': new_decisions,
        'total_decisions': len(records),
        't1_filled_this_week': t1_filled,
        't3_filled_this_week': t3_filled,
        't10_filled_this_week': t10_filled,
        'finalized_this_week': finalized,
        'top_wins': top_wins[:3],
        'top_losses': top_losses[:3],
    }


# ---------------------------------------------------------------------------
# 4-week trend
# ---------------------------------------------------------------------------

def _collect_trend_weeks(records: list[dict], current_week: date, n: int = 4) -> list[dict]:
    """Collect per-week stats for the last n ISO weeks ending at current_week."""
    trend = []
    for offset in range(n - 1, -1, -1):
        week_start = current_week - timedelta(weeks=offset)
        wk = iso_week_key(week_start)
        finalized_in_week = [
            r for r in records
            if (r.get('outcome_final') and _in_week((r.get('outcome_final') or {}).get('finalized_at', ''), wk))
        ]
        total = len(finalized_in_week)
        if total == 0:
            trend.append({'week': wk, 'sample': 0, 'ai_win': 'N/A', 'rule_win': 'N/A', 'tier1_win': 'N/A'})
            continue

        ai_wins = sum(1 for r in finalized_in_week
                      if (r.get('chain_sources') or {}).get('ai_bridge_action', '').replace('preview_', '') not in ('hold', '', None)
                      and (r.get('outcome_final') or {}).get('verdict') == 'win')
        rule_wins = sum(1 for r in finalized_in_week
                        if (r.get('chain_sources') or {}).get('rule_engine_action', '') not in ('hold', None)
                        and (r.get('outcome_final') or {}).get('verdict') == 'win')
        tier1_total = sum(1 for r in finalized_in_week if (r.get('chain_sources') or {}).get('consensus_tier') == 1)
        tier1_wins = sum(1 for r in finalized_in_week
                         if (r.get('chain_sources') or {}).get('consensus_tier') == 1
                         and (r.get('outcome_final') or {}).get('verdict') == 'win')

        ai_denominator = sum(1 for r in finalized_in_week
                             if (r.get('chain_sources') or {}).get('ai_bridge_action', '').replace('preview_', '') not in ('hold', '', None))
        rule_denominator = sum(1 for r in finalized_in_week
                               if (r.get('chain_sources') or {}).get('rule_engine_action', '') not in ('hold', None))

        trend.append({
            'week': wk,
            'sample': total,
            'ai_win': f'{ai_wins / ai_denominator:.0%}' if ai_denominator else 'N/A',
            'rule_win': f'{rule_wins / rule_denominator:.0%}' if rule_denominator else 'N/A',
            'tier1_win': f'{tier1_wins / tier1_total:.0%}' if tier1_total else 'N/A',
        })

    return trend


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def format_weekly_report(
    week_key: str,
    week_date: date,
    week_stats: dict,
    chain_breakdown: dict,
) -> str:
    period_start = _date_of_iso_week_start(week_key)
    period_end = period_start + timedelta(days=6)

    def pct(v):
        if v is None:
            return 'N/A'
        return f'{v:.1%}'

    def fmt_rate(bucket):
        wr = bucket.get('win_rate')
        lr = (bucket.get('loss', 0) / bucket.get('total', 1)) if bucket.get('total') else None
        fr = (bucket.get('flat', 0) / bucket.get('total', 1)) if bucket.get('total') else None
        return f"{pct(wr)} | {pct(lr)} | {pct(fr)}"

    rb = chain_breakdown or {}
    rule_b = rb.get('rule_engine', {})
    ai_b = rb.get('ai_bridge', {})
    tier1_b = rb.get('tier1_consensus', {})

    wins_lines = '\n'.join(
        f"{i+1}. {w['symbol']} — {w['window']} win (+{w['return_pct']}%)"
        for i, w in enumerate(week_stats.get('top_wins', []))
    ) or '（本週無 win 樣本）'

    losses_lines = '\n'.join(
        f"{i+1}. {l['symbol']} — {l['window']} loss ({l['return_pct']}%)"
        for i, l in enumerate(week_stats.get('top_losses', []))
    ) or '（本週無 loss 樣本）'

    lines = [
        f'---',
        f'title: ETF 決策品質週報 {week_key}',
        f'date: {week_date.isoformat()}',
        f'period: {period_start.isoformat()} ~ {period_end.isoformat()}',
        f'---',
        f'',
        f'## 本週摘要',
        f'- 新增決策建議：{week_stats["new_decisions"]} 筆',
        f'- 完成 T1 回填：{week_stats["t1_filled_this_week"]} 筆 / '
        f'T3：{week_stats["t3_filled_this_week"]} 筆 / '
        f'T10：{week_stats["t10_filled_this_week"]} 筆',
        f'- 本週到期完整樣本：{week_stats["finalized_this_week"]} 筆',
        f'',
        f'## 雙鏈勝率（累計）',
        f'| 鏈路 | 樣本數 | 勝率 | 敗率 | 平盤率 |',
        f'|------|--------|------|------|--------|',
        f'| 規則引擎 | {rule_b.get("total", 0)} | {fmt_rate(rule_b)} |',
        f'| AI Bridge | {ai_b.get("total", 0)} | {fmt_rate(ai_b)} |',
        f'| Tier 1 共識 | {tier1_b.get("total", 0)} | {fmt_rate(tier1_b)} |',
        f'',
        f'## 本週最準確標的（Top 3）',
        wins_lines,
        f'',
        f'## 本週最大失誤（Top 3）',
        losses_lines,
    ]

    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def write_weekly_report(content: str, week_key: str, wiki_dir: Path) -> dict:
    """Write content to dated file + latest symlink. Returns {'dated': Path, 'latest': Path}."""
    wiki_dir.mkdir(parents=True, exist_ok=True)

    dated_path = wiki_dir / f'decision-weekly-{week_key}.md'
    latest_path = wiki_dir / 'decision-quality-latest.md'

    dated_path.write_text(content, encoding='utf-8')
    latest_path.write_text(content, encoding='utf-8')

    return {'dated': dated_path, 'latest': latest_path}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    STATE = context.get_state_dir()
    provenance_path = STATE / 'decision_provenance.jsonl'
    quality_report_path = STATE / 'decision_quality_report.json'

    today = datetime.now(TW_TZ).date()
    # If run on Saturday, report covers the week just ended (Mon–Fri)
    # The current ISO week ends on Sunday, so Saturday is still current week
    week_key = iso_week_key(today)

    records = safe_load_jsonl(provenance_path) if provenance_path.exists() else []
    quality_report = safe_load_json(quality_report_path, {})
    chain_breakdown = quality_report.get('chain_breakdown', {})

    week_stats = collect_week_stats(records, today)
    content = format_weekly_report(week_key, today, week_stats, chain_breakdown)
    paths = write_weekly_report(content, week_key, WIKI_DIR)

    print(f"GENERATE_DECISION_QUALITY_WEEKLY_OK:"
          f"week={week_key} "
          f"new={week_stats['new_decisions']} "
          f"finalized={week_stats['finalized_this_week']} "
          f"dated={paths['dated'].name}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run the weekly report tests**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_generate_decision_quality_weekly.py -v --tb=short
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

Expected: 365+ passed, 0 failures.

- [ ] **Step 6: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/generate_decision_quality_weekly.py \
        skills/ETF_TW/tests/test_generate_decision_quality_weekly.py
git commit -m "feat(weekly): add generate_decision_quality_weekly.py — Saturday wiki report"
```

---

## Task 4: Add 2 cron jobs to `cron/jobs.json`

**Files:**
- Modify: `cron/jobs.json`

### Background

Two new jobs per design spec:
- **ETF 決策自動復盤** at `5 15 * * 1-5` (15:05 weekdays) — runs `sync_decision_reviews.py`
- **ETF 決策品質週報** at `5 9 * * 6` (09:05 Saturday) — runs `generate_decision_quality_weekly.py`

Both are script-driven (not LLM prompt) jobs, following the `worldmonitor_daily` pattern in the existing `cron/jobs.json`. They use `"script"` field instead of `"prompt"`.

Note: Cron jobs use script field with basename only; the `ETF_TW/scripts/` resolution is handled by the Hermes cron scheduler per existing jobs (see `worldmonitor_daily` which uses `"script": "sync_worldmonitor_daily.py"`).

- [ ] **Step 1: Read current cron/jobs.json to confirm structure**

Verify the last job entry to confirm closing bracket position. The file ends with `"updated_at": "..."` and `}` at the root level. New jobs go in `"jobs": [...]`.

- [ ] **Step 2: Add the two new jobs**

In `cron/jobs.json`, add to the `"jobs"` array (before the closing `]`) the following two objects:

```json
    {
      "id": "decision_auto_review",
      "name": "ETF 決策自動復盤",
      "prompt": "執行 ETF 決策自動 T+N 回填（script 已自動執行，請引用 script 輸出並簡短摘要填入欄位狀況）",
      "script": "sync_decision_reviews.py",
      "skills": [],
      "skill": null,
      "model": null,
      "provider": null,
      "base_url": null,
      "schedule": {
        "kind": "cron",
        "expr": "5 15 * * 1-5",
        "display": "5 15 * * 1-5"
      },
      "schedule_display": "5 15 * * 1-5",
      "repeat": {
        "times": null,
        "completed": 0
      },
      "enabled": true,
      "state": "scheduled",
      "paused_at": null,
      "paused_reason": null,
      "created_at": "2026-04-19T00:00:00+08:00",
      "next_run_at": null,
      "last_run_at": null,
      "last_status": null,
      "last_error": null,
      "deliver": "telegram",
      "origin": {
        "platform": "telegram",
        "chat_id": "",
        "chat_name": "",
        "thread_id": null
      },
      "last_delivery_error": null
    },
    {
      "id": "decision_quality_weekly",
      "name": "ETF 決策品質週報",
      "prompt": "執行 ETF 決策品質週報產出（script 已自動執行，請引用 script 輸出並確認 wiki/decision-quality-latest.md 已更新）",
      "script": "generate_decision_quality_weekly.py",
      "skills": [],
      "skill": null,
      "model": null,
      "provider": null,
      "base_url": null,
      "schedule": {
        "kind": "cron",
        "expr": "5 9 * * 6",
        "display": "5 9 * * 6"
      },
      "schedule_display": "5 9 * * 6",
      "repeat": {
        "times": null,
        "completed": 0
      },
      "enabled": true,
      "state": "scheduled",
      "paused_at": null,
      "paused_reason": null,
      "created_at": "2026-04-19T00:00:00+08:00",
      "next_run_at": null,
      "last_run_at": null,
      "last_status": null,
      "last_error": null,
      "deliver": "telegram",
      "origin": {
        "platform": "telegram",
        "chat_id": "",
        "chat_name": "",
        "thread_id": null
      },
      "last_delivery_error": null
    }
```

- [ ] **Step 3: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('cron/jobs.json')); print('JSON valid')"
```

Expected: `JSON valid`

- [ ] **Step 4: Verify job count ≥ 9**

```bash
python3 -c "
import json
with open('cron/jobs.json') as f:
    d = json.load(f)
jobs = d if isinstance(d, list) else d.get('jobs', [])
print(f'{len(jobs)} jobs')
"
```

Expected: `9 jobs`

- [ ] **Step 5: Run full test suite (no regressions)**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3
```

Expected: 365+ passed.

- [ ] **Step 6: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add cron/jobs.json
git commit -m "feat(cron): add ETF 決策自動復盤 (15:05) and ETF 決策品質週報 (09:05 Sat)"
```

---

## Task 5: End-to-end smoke test + verify_deployment update

**Files:**
- Test: `tests/test_sync_decision_reviews.py` (add integration test)
- Modify: `scripts/verify_deployment.sh`

### Background

Add an end-to-end smoke test that:
1. Creates a temporary provenance JSONL with one record whose T1 window is due
2. Provides a mock market_cache with a fresh price
3. Calls `run_backfill()` directly
4. Asserts T1 is filled and `outcome_final` is still null (T3/T10 not yet due)

Also update `verify_deployment.sh` cron count threshold from 7 → 9.

- [ ] **Step 1: Write the integration test**

Add to `tests/test_sync_decision_reviews.py`:

```python
def test_run_backfill_fills_t1(tmp_path):
    """Integration: run_backfill fills T1 when 1 trading day has elapsed."""
    import json
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from sync_decision_reviews import run_backfill

    TW_TZ = ZoneInfo('Asia/Taipei')

    # Create a record created 2 trading days ago so T1 (1 day) is due
    created_at = (datetime.now(TW_TZ) - timedelta(days=3)).isoformat()
    provenance_path = tmp_path / 'decision_provenance.jsonl'
    record = {
        'decision_id': 'smoke-001',
        'created_at': created_at,
        'source': 'run_auto_decision_scan',
        'outputs': {'symbol': '00878', 'reference_price': 20.0, 'action': 'buy-preview'},
        'chain_sources': None,
        'review_lifecycle': {'T1': None, 'T3': None, 'T10': None},
        'outcome_final': None,
        'tags': [],
    }
    provenance_path.write_text(json.dumps(record, ensure_ascii=False) + '\n')

    fresh_ts = datetime.now(TW_TZ).isoformat()
    market_cache = {
        'quotes': {
            '00878': {'current_price': 20.4, 'updated_at': fresh_ts}
        }
    }

    quality_report_path = tmp_path / 'decision_quality_report.json'

    stats = run_backfill(provenance_path, market_cache, quality_report_path)

    # T1 must be filled
    from etf_core.state_io import safe_load_jsonl
    rows = safe_load_jsonl(provenance_path)
    assert len(rows) == 1
    t1 = rows[0]['review_lifecycle']['T1']
    assert t1 is not None
    assert t1['verdict'] in ('win', 'loss', 'flat')
    assert t1['source'] == 'market_cache'
    assert stats['filled'] >= 1

    # quality report should have been written
    assert quality_report_path.exists()
```

- [ ] **Step 2: Run the integration test**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sync_decision_reviews.py::test_run_backfill_fills_t1 -v --tb=short
```

Expected: PASS

- [ ] **Step 3: Update cron job count threshold in `verify_deployment.sh`**

In `scripts/verify_deployment.sh`, find line:

```bash
if [[ "$JOB_COUNT" -ge 7 ]]; then
```

Change to:

```bash
if [[ "$JOB_COUNT" -ge 9 ]]; then
```

- [ ] **Step 4: Run full test suite one final time**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

Expected: 366+ passed, 0 failures.

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/tests/test_sync_decision_reviews.py \
        skills/ETF_TW/scripts/verify_deployment.sh
git commit -m "test(e2e): add run_backfill integration smoke test; update cron count threshold to 9"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Requirement | Covered By |
|-----------------|-----------|
| T+N 到期計算（排除週末） | Task 2: `trading_days_between()`, tested |
| market_cache → yfinance fallback | Task 2: `get_closing_price()`, tested |
| verdict 判定 ±1.5% | Task 2: `determine_verdict()`, tested |
| T+N 欄位格式（reviewed_at, price_then, reference_price, return_pct, verdict, source） | Task 2: `review_data` dict in `run_backfill()` |
| outcome_final 多數決 + tiebreak to T10 | Task 2: `compute_outcome_final()`, tested |
| chain_sources 欄位 | Task 1: `build_provenance_record()`, tested |
| decision_quality_report.json chain_breakdown | Task 2: `update_chain_breakdown()`, tested |
| 週報寫入 wiki/decision-weekly-YYYY-WNN.md | Task 3: `write_weekly_report()`, tested |
| wiki/decision-quality-latest.md 固定路徑 | Task 3: `write_weekly_report()`, tested |
| cron 15:05 + 09:05 Sat | Task 4: cron/jobs.json |
| verify_deployment.sh 9 jobs | Task 5 |

### 2. Placeholder Scan

No TBD, TODO, or incomplete steps found.

### 3. Type Consistency

- `build_provenance_record()` signature: `chain_sources: dict | None = None` — used consistently in Task 1 call and tests.
- `run_backfill()` signature: `(provenance_path: Path, market_cache: dict, quality_report_path: Path) -> dict` — matches integration test call in Task 5.
- `write_weekly_report()` returns `{'dated': Path, 'latest': Path}` — matches test assertion.
- `collect_week_stats()` returns dict with `new_decisions`, `total_decisions`, `t1_filled_this_week`, etc. — matches `format_weekly_report()` usage.
