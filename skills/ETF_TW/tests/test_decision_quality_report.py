"""
test_decision_quality_report.py — QUALITY-01

Contract tests for generate_decision_quality_report.generate_report().
Uses inline fixture data only — no real state file I/O.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_decision_quality_report import generate_report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_empty_records_all_zeros():
    report = generate_report([])
    assert "strategy_alignment_rate" in report
    assert "confidence_distribution" in report
    assert "interception_rate" in report
    assert "tier_distribution" in report
    assert "win_rate" in report
    assert "total_decisions" in report
    assert "last_updated" in report
    assert report["strategy_alignment_rate"] == 0.0
    assert report["interception_rate"] == 0.0
    assert report["total_decisions"] == 0
    assert report["confidence_distribution"] == {"high": 0, "medium": 0, "low": 0}
    assert report["tier_distribution"] == {"tier1": 0, "tier2": 0, "tier3": 0}


def test_strategy_alignment_rate_calculation():
    records = [{"strategy_alignment": True}] * 7 + [{"strategy_alignment": False}] * 3
    report = generate_report(records)
    assert report["strategy_alignment_rate"] == 70.0


def test_interception_rate_calculation():
    records = (
        [{"pre_flight_intercepted": True}] * 5
        + [{"pre_flight_intercepted": False}] * 15
    )
    report = generate_report(records)
    assert report["interception_rate"] == 25.0


def test_confidence_distribution_buckets():
    records = [
        {"confidence": 0.9},
        {"confidence": 0.9},
        {"confidence": 0.6},
        {"confidence": 0.4},
    ]
    report = generate_report(records)
    dist = report["confidence_distribution"]
    assert dist["high"] == 2
    assert dist["medium"] == 2  # 0.6 and 0.4 are both in [0.4, 0.7)
    assert dist["low"] == 0


def test_tier_distribution():
    records = [
        {"tier": 1},
        {"tier": 1},
        {"tier": 2},
        {"tier": 3},
    ]
    report = generate_report(records)
    assert report["tier_distribution"] == {"tier1": 2, "tier2": 1, "tier3": 1}


def test_win_rate_is_null_placeholder():
    report = generate_report([{"action": "preview_buy"}])
    assert report["win_rate"] is None


def test_last_updated_is_iso_string():
    report = generate_report([])
    # Should not raise
    dt = datetime.fromisoformat(report["last_updated"])
    assert dt is not None


def test_missing_optional_fields_no_error():
    """Records with no confidence/tier/strategy_alignment keys must not raise."""
    records = [
        {"action": "hold", "outcome_status": "tracked"},
        {"action": "preview_buy"},
        {},
    ]
    report = generate_report(records)
    assert report["total_decisions"] == 3
    assert report["strategy_alignment_rate"] == 0.0
    assert report["confidence_distribution"] == {"high": 0, "medium": 0, "low": 0}
    assert report["tier_distribution"] == {"tier1": 0, "tier2": 0, "tier3": 0}
