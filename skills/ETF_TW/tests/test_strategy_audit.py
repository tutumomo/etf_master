"""
Tests for strategy_audit.py:
  - run_strategy_audit() with empty / populated provenance records
  - format_strategy_audit_section() output structure
  - Strategy switch counting
  - Alignment rate computation
"""
import pytest
from pathlib import Path
from scripts.strategy_audit import run_strategy_audit, format_strategy_audit_section


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_record(base_strategy, strategy_aligned=True, score=6.0, symbol="0050",
                 group="income", verdict=None):
    rec = {
        "strategy_snapshot": {"base_strategy": base_strategy, "scenario_overlay": "無"},
        "inputs_digest": {"base_strategy": base_strategy},
        "outputs": {
            "action": "preview_buy",
            "symbol": symbol,
            "score": score,
            "strategy_aligned": strategy_aligned,
            "all_candidates_top3": [
                {"symbol": symbol, "score": score, "group": group}
            ],
        },
        "review_lifecycle": {
            "T1": {"verdict": verdict, "return_pct": 2.0} if verdict else None,
            "T3": None,
            "T10": None,
        },
        "outcome_final": None,
    }
    return rec


def _write_jsonl(tmp_path, records):
    import json
    p = tmp_path / "decision_provenance.jsonl"
    p.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# Empty / missing file
# ---------------------------------------------------------------------------

def test_empty_provenance_returns_zeros(tmp_path):
    p = tmp_path / "decision_provenance.jsonl"
    audit = run_strategy_audit(p)
    assert audit["total_records"] == 0
    assert audit["strategy_switch_count"] == 0
    assert audit["strategy_distribution"] == {}


def test_missing_file_returns_empty(tmp_path):
    audit = run_strategy_audit(tmp_path / "nonexistent.jsonl")
    assert audit["total_records"] == 0


# ---------------------------------------------------------------------------
# Strategy distribution
# ---------------------------------------------------------------------------

def test_strategy_distribution_counts(tmp_path):
    records = [
        _make_record("收益優先"),
        _make_record("收益優先"),
        _make_record("核心累積"),
    ]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    assert audit["strategy_distribution"]["收益優先"] == 2
    assert audit["strategy_distribution"]["核心累積"] == 1
    assert audit["total_records"] == 3


# ---------------------------------------------------------------------------
# Alignment rate
# ---------------------------------------------------------------------------

def test_alignment_rate_all_aligned(tmp_path):
    records = [_make_record("收益優先", strategy_aligned=True) for _ in range(4)]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    assert audit["alignment_rate_by_strategy"]["收益優先"] == 1.0


def test_alignment_rate_mixed(tmp_path):
    records = [
        _make_record("收益優先", strategy_aligned=True),
        _make_record("收益優先", strategy_aligned=True),
        _make_record("收益優先", strategy_aligned=False),
        _make_record("收益優先", strategy_aligned=False),
    ]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    assert audit["alignment_rate_by_strategy"]["收益優先"] == 0.5


# ---------------------------------------------------------------------------
# Strategy switch counting
# ---------------------------------------------------------------------------

def test_strategy_switch_counts_transitions(tmp_path):
    records = [
        _make_record("收益優先"),
        _make_record("收益優先"),
        _make_record("核心累積"),   # switch 1
        _make_record("核心累積"),
        _make_record("防守保守"),   # switch 2
    ]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    assert audit["strategy_switch_count"] == 2


def test_no_switches_same_strategy(tmp_path):
    records = [_make_record("核心累積") for _ in range(5)]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    assert audit["strategy_switch_count"] == 0


# ---------------------------------------------------------------------------
# Win rate by alignment
# ---------------------------------------------------------------------------

def test_win_rate_by_alignment(tmp_path):
    records = [
        _make_record("收益優先", strategy_aligned=True, verdict="win"),
        _make_record("收益優先", strategy_aligned=True, verdict="win"),
        _make_record("收益優先", strategy_aligned=False, verdict="loss"),
    ]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    aligned_wr = audit["win_rate_by_alignment"]["aligned"]
    assert aligned_wr["win_rate"] == 1.0
    assert aligned_wr["total"] == 2
    not_aligned_wr = audit["win_rate_by_alignment"]["not_aligned"]
    assert not_aligned_wr["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def test_format_section_empty():
    section = format_strategy_audit_section({"total_records": 0})
    assert "尚無" in section


def test_format_section_has_required_headings(tmp_path):
    records = [
        _make_record("收益優先", strategy_aligned=True, verdict="win"),
        _make_record("核心累積", strategy_aligned=False, verdict="loss"),
    ]
    p = _write_jsonl(tmp_path, records)
    audit = run_strategy_audit(p)
    section = format_strategy_audit_section(audit)
    assert "策略影響力稽核" in section
    assert "策略分佈" in section
    assert "策略切換次數" in section
    assert "策略對齊 vs 非對齊勝率" in section
