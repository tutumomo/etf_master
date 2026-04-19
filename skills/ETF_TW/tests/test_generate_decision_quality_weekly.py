"""Tests for generate_decision_quality_weekly.py."""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, date, timedelta
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