"""
Tests for auto_calibrate_thresholds.py

Run: cd skills/ETF_TW && .venv/bin/python3 -m pytest tests/test_auto_calibrate_thresholds.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from auto_calibrate_thresholds import (
    DEFAULT_THRESHOLDS,
    MAX_STEP,
    MIN_SAMPLES,
    THRESHOLD_BOUNDS,
    WIN_RATE_HIGH,
    WIN_RATE_LOW,
    compute_calibration,
    load_current_thresholds,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def defaults():
    return dict(DEFAULT_THRESHOLDS)


def _make_breakdown(total: int, win_rate: float | None) -> dict:
    """Build a minimal chain_breakdown with rule_engine stats."""
    win = int(total * win_rate) if win_rate is not None and total > 0 else 0
    return {
        "rule_engine": {
            "total": total,
            "win": win,
            "win_rate": win_rate,
        }
    }


# ---------------------------------------------------------------------------
# compute_calibration — suggestion layer
# ---------------------------------------------------------------------------

class TestComputeCalibrationSuggestion:
    def test_insufficient_samples_no_auto_apply(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES - 1, win_rate=0.20)
        result = compute_calibration(breakdown, defaults)
        assert result["auto_apply"] is False

    def test_null_win_rate_no_auto_apply(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES + 5, win_rate=None)
        result = compute_calibration(breakdown, defaults)
        assert result["auto_apply"] is False

    def test_normal_win_rate_no_auto_apply(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES + 5, win_rate=0.50)
        result = compute_calibration(breakdown, defaults)
        assert result["auto_apply"] is False

    def test_suggestions_always_present(self, defaults):
        breakdown = _make_breakdown(total=5, win_rate=None)
        result = compute_calibration(breakdown, defaults)
        assert set(result["suggestions"].keys()) == set(DEFAULT_THRESHOLDS.keys())

    def test_suggestion_delta_zero_when_no_change(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES + 5, win_rate=0.50)
        result = compute_calibration(breakdown, defaults)
        for s in result["suggestions"].values():
            assert s["delta"] == 0.0


# ---------------------------------------------------------------------------
# compute_calibration — auto-apply (hardcoded threshold trigger)
# ---------------------------------------------------------------------------

class TestComputeCalibrationAutoApply:
    def test_low_win_rate_triggers_tighten(self, defaults):
        """win_rate < WIN_RATE_LOW → 門檻 +MAX_STEP"""
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=WIN_RATE_LOW - 0.01)
        result = compute_calibration(breakdown, defaults)
        assert result["auto_apply"] is True
        for level, s in result["suggestions"].items():
            assert s["delta"] == pytest.approx(MAX_STEP, abs=1e-6) or \
                   s["suggested"] == THRESHOLD_BOUNDS[level][1]  # clamped at max

    def test_high_win_rate_triggers_relax(self, defaults):
        """win_rate >= WIN_RATE_HIGH → 門檻 -MAX_STEP"""
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=WIN_RATE_HIGH)
        result = compute_calibration(breakdown, defaults)
        assert result["auto_apply"] is True
        for level, s in result["suggestions"].items():
            assert s["delta"] == pytest.approx(-MAX_STEP, abs=1e-6) or \
                   s["suggested"] == THRESHOLD_BOUNDS[level][0]  # clamped at min

    def test_new_thresholds_within_bounds(self, defaults):
        """套用後門檻不得超出 THRESHOLD_BOUNDS。"""
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=0.10)
        result = compute_calibration(breakdown, defaults)
        for level, val in result["new_thresholds"].items():
            lo, hi = THRESHOLD_BOUNDS[level]
            assert lo <= val <= hi, f"{level}: {val} outside [{lo}, {hi}]"

    def test_step_capped_at_max_step(self, defaults):
        """每次調整幅度不超過 MAX_STEP。"""
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=0.10)
        result = compute_calibration(breakdown, defaults)
        for level, s in result["suggestions"].items():
            assert abs(s["delta"]) <= MAX_STEP + 1e-6

    def test_new_thresholds_equals_current_when_no_apply(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES + 5, win_rate=0.50)
        result = compute_calibration(breakdown, defaults)
        assert result["new_thresholds"] == defaults

    def test_new_thresholds_differs_when_applied(self, defaults):
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=0.10)
        result = compute_calibration(breakdown, defaults)
        assert result["new_thresholds"] != defaults


# ---------------------------------------------------------------------------
# compute_calibration — clamping at boundary
# ---------------------------------------------------------------------------

class TestThresholdClamping:
    def test_clamp_at_upper_bound(self):
        """已達上限的門檻不再增加。"""
        at_max = {k: THRESHOLD_BOUNDS[k][1] for k in DEFAULT_THRESHOLDS}
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=0.10)
        result = compute_calibration(breakdown, at_max)
        for level, val in result["new_thresholds"].items():
            assert val == THRESHOLD_BOUNDS[level][1]

    def test_clamp_at_lower_bound(self):
        """已達下限的門檻不再降低。"""
        at_min = {k: THRESHOLD_BOUNDS[k][0] for k in DEFAULT_THRESHOLDS}
        breakdown = _make_breakdown(total=MIN_SAMPLES, win_rate=1.0)
        result = compute_calibration(breakdown, at_min)
        for level, val in result["new_thresholds"].items():
            assert val == THRESHOLD_BOUNDS[level][0]


# ---------------------------------------------------------------------------
# load_current_thresholds — state I/O
# ---------------------------------------------------------------------------

class TestLoadCurrentThresholds:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        result = load_current_thresholds(tmp_path)
        assert result == DEFAULT_THRESHOLDS

    def test_reads_saved_values(self, tmp_path):
        saved = {"low": 3.0, "normal": 4.5, "elevated": 5.5, "high": 6.5}
        (tmp_path / "calibrated_thresholds.json").write_text(
            json.dumps(saved), encoding="utf-8"
        )
        result = load_current_thresholds(tmp_path)
        assert result == saved

    def test_partial_file_falls_back_to_defaults(self, tmp_path):
        """部分欄位缺失時，缺失鍵回傳預設值。"""
        (tmp_path / "calibrated_thresholds.json").write_text(
            json.dumps({"low": 3.0}), encoding="utf-8"
        )
        result = load_current_thresholds(tmp_path)
        assert result["low"] == 3.0
        assert result["normal"] == DEFAULT_THRESHOLDS["normal"]

    def test_invalid_json_falls_back_to_defaults(self, tmp_path):
        (tmp_path / "calibrated_thresholds.json").write_text(
            "not-json", encoding="utf-8"
        )
        result = load_current_thresholds(tmp_path)
        assert result == DEFAULT_THRESHOLDS
