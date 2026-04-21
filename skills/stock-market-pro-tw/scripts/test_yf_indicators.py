#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pytest>=8.0.0",
#   "pandas>=2.0.0",
#   "numpy>=1.24.0",
# ]
# ///
"""
Tests for technical indicator pure functions in yf.py.

Run with: uv run pytest test_yf_indicators.py -v
"""
from __future__ import annotations

import math
import sys
import types
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

# yf.py has top-level imports of optional chart libs (plotille, mplfinance, matplotlib,
# rich) that are not available in all test environments. Use MagicMock-based stubs so
# that `from rich.console import Console` and similar work without the real packages.
import unittest.mock as _mock

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    # Module-level __getattr__ takes only (attr), not (self, attr)
    mod.__getattr__ = lambda attr: _mock.MagicMock()  # type: ignore[method-assign]
    return mod

for _mod_name in ["plotille", "mplfinance",
                  "rich", "rich.console", "rich.table", "rich.panel", "rich.text"]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

# matplotlib.use() must be callable at module level
if "matplotlib" not in sys.modules:
    _mpl = _make_stub("matplotlib")
    _mpl.use = _mock.MagicMock()  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = _mpl
if "matplotlib.pyplot" not in sys.modules:
    sys.modules["matplotlib.pyplot"] = _make_stub("matplotlib.pyplot")

# rich top-level `print` alias used in yf.py
sys.modules["rich"].print = _mock.MagicMock()  # type: ignore[attr-defined]

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yf import _has_data, calc_rsi, calc_macd, calc_bbands


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_close(n: int = 60, start: float = 100.0, step: float = 1.0) -> pd.Series:
    """Monotonically increasing price series."""
    return pd.Series([start + i * step for i in range(n)], dtype=float)


def _make_volatile_close(n: int = 60) -> pd.Series:
    """Oscillating price series to produce non-trivial RSI."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, n)
    prices = 100.0 * np.exp(np.cumsum(returns))
    return pd.Series(prices, dtype=float)


# ---------------------------------------------------------------------------
# _has_data
# ---------------------------------------------------------------------------

class TestHasData:
    def test_normal_series_returns_true(self):
        assert _has_data(pd.Series([1.0, 2.0, 3.0])) is True

    def test_all_nan_returns_false(self):
        assert _has_data(pd.Series([float("nan"), float("nan")])) is False

    def test_empty_series_returns_false(self):
        assert _has_data(pd.Series([], dtype=float)) is False

    def test_none_returns_false(self):
        assert _has_data(None) is False  # type: ignore[arg-type]

    def test_series_with_leading_nans_returns_true(self):
        s = pd.Series([float("nan"), float("nan"), 3.0])
        assert _has_data(s) is True


# ---------------------------------------------------------------------------
# calc_rsi
# ---------------------------------------------------------------------------

class TestCalcRsi:
    def test_output_length_matches_input(self):
        close = _make_close(60)
        rsi = calc_rsi(close, window=14)
        assert len(rsi) == len(close)

    def test_values_in_range_0_to_100(self):
        close = _make_volatile_close(60)
        rsi = calc_rsi(close, window=14)
        valid = rsi.dropna()
        assert len(valid) > 0
        assert (valid >= 0).all(), "RSI has values below 0"
        assert (valid <= 100).all(), "RSI has values above 100"

    def test_monotone_up_rsi_all_nan(self):
        """Pure uptrend → avg_loss=0, replaced with NA → RSI is all NaN (by design)."""
        close = _make_close(60, step=1.0)
        rsi = calc_rsi(close, window=14)
        # calc_rsi replaces avg_loss=0 with pd.NA so RS diverges; result is all NaN
        assert rsi.dropna().empty, "Expected all-NaN RSI for pure uptrend (loss=0 → NA)"

    def test_monotone_down_rsi_near_0(self):
        """Pure downtrend → RSI should be low (<= 10)."""
        close = _make_close(60, step=-1.0)
        rsi = calc_rsi(close, window=14)
        last_valid = rsi.dropna().iloc[-1]
        assert last_valid <= 10.0, f"Expected RSI near 0 for downtrend, got {last_valid:.2f}"

    def test_warm_up_period_is_nan(self):
        """First `window` values should be NaN (EWM min_periods)."""
        window = 14
        close = _make_close(60)
        rsi = calc_rsi(close, window=window)
        # EWM with min_periods=window: first window-1 entries are NaN
        assert rsi.iloc[:window - 1].isna().all()

    def test_custom_window(self):
        close = _make_volatile_close(60)
        rsi = calc_rsi(close, window=7)
        assert rsi.dropna().between(0, 100).all()


# ---------------------------------------------------------------------------
# calc_macd
# ---------------------------------------------------------------------------

class TestCalcMacd:
    def test_returns_three_series(self):
        close = _make_close(60)
        result = calc_macd(close)
        assert len(result) == 3

    def test_output_lengths_match_input(self):
        close = _make_close(60)
        macd, sig, hist = calc_macd(close)
        assert len(macd) == len(close)
        assert len(sig) == len(close)
        assert len(hist) == len(close)

    def test_histogram_equals_macd_minus_signal(self):
        close = _make_volatile_close(60)
        macd, sig, hist = calc_macd(close)
        expected_hist = macd - sig
        pd.testing.assert_series_equal(hist, expected_hist)

    def test_warm_up_nans_present(self):
        """With slow=26, first 25 values of macd should be NaN."""
        close = _make_close(60)
        macd, sig, hist = calc_macd(close, fast=12, slow=26, signal=9)
        assert macd.iloc[:25].isna().all()

    def test_uptrend_macd_positive(self):
        """In a strong uptrend fast EMA > slow EMA → MACD > 0."""
        close = _make_close(100, step=2.0)
        macd, _, _ = calc_macd(close)
        assert macd.dropna().iloc[-1] > 0


# ---------------------------------------------------------------------------
# calc_bbands
# ---------------------------------------------------------------------------

class TestCalcBbands:
    def test_returns_three_series(self):
        close = _make_close(60)
        result = calc_bbands(close)
        assert len(result) == 3

    def test_upper_ge_mid_ge_lower(self):
        """upper ≥ mid ≥ lower for all non-NaN rows."""
        close = _make_volatile_close(60)
        upper, mid, lower = calc_bbands(close, window=20)
        mask = upper.notna() & mid.notna() & lower.notna()
        assert (upper[mask] >= mid[mask]).all(), "upper < mid detected"
        assert (mid[mask] >= lower[mask]).all(), "mid < lower detected"

    def test_warm_up_nans(self):
        """First window-1 values should be NaN."""
        window = 20
        close = _make_close(60)
        upper, mid, lower = calc_bbands(close, window=window)
        assert upper.iloc[:window - 1].isna().all()
        assert mid.iloc[:window - 1].isna().all()
        assert lower.iloc[:window - 1].isna().all()

    def test_mid_is_rolling_mean(self):
        close = _make_volatile_close(60)
        _, mid, _ = calc_bbands(close, window=20)
        expected_mid = close.rolling(window=20, min_periods=20).mean()
        pd.testing.assert_series_equal(mid, expected_mid)

    def test_wider_std_produces_wider_bands(self):
        """n_std=3 bands should be wider than n_std=2 bands."""
        close = _make_volatile_close(60)
        upper2, _, lower2 = calc_bbands(close, window=20, n_std=2.0)
        upper3, _, lower3 = calc_bbands(close, window=20, n_std=3.0)
        mask = upper2.notna()
        assert (upper3[mask] >= upper2[mask]).all()
        assert (lower3[mask] <= lower2[mask]).all()

    def test_flat_price_zero_width_bands(self):
        """Constant price → std=0 → upper == mid == lower."""
        close = pd.Series([50.0] * 40, dtype=float)
        upper, mid, lower = calc_bbands(close, window=20)
        valid = upper.dropna()
        assert (valid == 50.0).all()
        pd.testing.assert_series_equal(upper.dropna(), lower.dropna())
