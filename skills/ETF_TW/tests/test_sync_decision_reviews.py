"""Tests for sync_decision_reviews.py and provenance chain_sources field."""
import sys
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

TW_TZ = ZoneInfo('Asia/Taipei')


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


def test_build_provenance_record_without_chain_sources():
    """build_provenance_record() defaults chain_sources to None when not provided."""
    from provenance_logger import build_provenance_record

    request_payload = {
        'request_id': 'test-002',
        'inputs': {
            'strategy': {'base_strategy': '平衡配置', 'scenario_overlay': '無'},
            'positions': {'holdings': [], 'positions': []},
            'market_context_taiwan': {},
            'market_event_context': {},
            'intraday_tape_context': {},
            'portfolio_snapshot': {},
            'orders_open': {},
        }
    }
    response_payload = {
        'request_id': 'test-002',
        'decision': {'action': 'hold', 'confidence': 'medium', 'summary': 'test'},
        'candidate': {'symbol': None, 'reference_price': None, 'quantity': None},
    }

    record = build_provenance_record(
        request_payload=request_payload,
        response_payload=response_payload,
        source='test',
    )

    assert record['chain_sources'] is None


# ---------------------------------------------------------------------------
# sync_decision_reviews tests
# ---------------------------------------------------------------------------

def test_trading_days_between_excludes_weekends():
    """Count of trading days between two dates excludes Sat/Sun."""
    from sync_decision_reviews import trading_days_between

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


def test_get_closing_price_stale_cache_returns_skip():
    """get_closing_price() skips stale cache (>6 hours old)."""
    from sync_decision_reviews import get_closing_price

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
    assert result['chain_breakdown']['ai_bridge']['total'] == 1
    assert result['chain_breakdown']['ai_bridge']['win'] == 1
    assert result['chain_breakdown']['tier1_consensus']['total'] == 1
    assert result['chain_breakdown']['tier1_consensus']['win'] == 1
    assert result['total_decisions_with_outcome'] == 2


def test_run_backfill_fills_t1(tmp_path):
    """Integration: run_backfill fills T1 when 1 trading day has elapsed."""
    from sync_decision_reviews import run_backfill
    from etf_core.state_io import safe_load_jsonl

    # Create a record created 3 calendar days ago (ensures ≥1 trading day elapsed)
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
    rows = safe_load_jsonl(provenance_path)
    assert len(rows) == 1
    t1 = rows[0]['review_lifecycle']['T1']
    assert t1 is not None
    assert t1['verdict'] in ('win', 'loss', 'flat')
    assert t1['source'] == 'market_cache'
    assert stats['filled'] >= 1

    # quality report should have been written
    assert quality_report_path.exists()