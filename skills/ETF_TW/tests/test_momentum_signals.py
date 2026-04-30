"""
Tests for auto_trade.momentum_signals (F1 計畫):
  - compute_relative_momentum: 個股 vs 大盤的相對報酬
  - is_momentum_reversal: 兩個條件 AND 判斷
  - 邊界：缺資料 / 完全跟上大盤 / 反轉訊號
"""
from __future__ import annotations

import pytest

from scripts.auto_trade.momentum_signals import (
    compute_relative_momentum,
    is_momentum_reversal,
    MOMENTUM_GAP_THRESHOLD,
    RSI_OVERSOLD_THRESHOLD,
    MomentumSignal,
)


# ---------------------------------------------------------------------------
# compute_relative_momentum
# ---------------------------------------------------------------------------

def test_relative_momentum_underperformance():
    """個股 -15% vs 大盤 -3% → 相對 -12%"""
    rel = compute_relative_momentum(symbol_return_20d=-0.15, market_return_20d=-0.03)
    assert rel == pytest.approx(-0.12)


def test_relative_momentum_outperformance():
    """個股 +20% vs 大盤 +5% → 相對 +15%"""
    rel = compute_relative_momentum(symbol_return_20d=0.20, market_return_20d=0.05)
    assert rel == pytest.approx(0.15)


def test_relative_momentum_in_line():
    """跟上大盤 → 相對 0"""
    rel = compute_relative_momentum(symbol_return_20d=0.05, market_return_20d=0.05)
    assert rel == pytest.approx(0.0)


def test_relative_momentum_missing_inputs():
    """任一缺值 → None"""
    assert compute_relative_momentum(symbol_return_20d=None, market_return_20d=0.05) is None
    assert compute_relative_momentum(symbol_return_20d=0.05, market_return_20d=None) is None
    assert compute_relative_momentum(symbol_return_20d=None, market_return_20d=None) is None


# ---------------------------------------------------------------------------
# is_momentum_reversal
# ---------------------------------------------------------------------------

def test_reversal_when_gap_below_minus10_and_rsi_below_40():
    """跑輸大盤 -12% 且 RSI=35 → 觸發"""
    sig = is_momentum_reversal(relative_momentum=-0.12, rsi=35)
    assert sig.triggered is True
    assert sig.reason == "underperform_and_oversold"
    assert sig.relative_momentum == pytest.approx(-0.12)
    assert sig.rsi == 35


def test_reversal_skipped_when_gap_above_minus10():
    """跑輸僅 -8%，未達 -10% 門檻 → 不觸發"""
    sig = is_momentum_reversal(relative_momentum=-0.08, rsi=35)
    assert sig.triggered is False
    assert "underperform_threshold" in sig.reason


def test_reversal_skipped_when_rsi_above_40():
    """RSI=45 不夠弱 → 不觸發（即使 underperform 達標）"""
    sig = is_momentum_reversal(relative_momentum=-0.15, rsi=45)
    assert sig.triggered is False
    assert "rsi_too_strong" in sig.reason


def test_reversal_skipped_when_outperforming():
    """個股贏大盤 → 即使 RSI 弱也不觸發"""
    sig = is_momentum_reversal(relative_momentum=0.05, rsi=35)
    assert sig.triggered is False


def test_reversal_skipped_when_missing_data():
    """relative_momentum=None → 不觸發"""
    sig = is_momentum_reversal(relative_momentum=None, rsi=35)
    assert sig.triggered is False
    assert sig.reason == "missing_data"
    sig2 = is_momentum_reversal(relative_momentum=-0.15, rsi=None)
    assert sig2.triggered is False
    assert sig2.reason == "missing_data"


def test_reversal_at_exact_thresholds():
    """邊界精確值：gap = -10% 與 RSI = 40 都「未達觸發門檻」（嚴格 < / >）"""
    # gap == -10% → 不觸發（要嚴格 < -10%）
    sig1 = is_momentum_reversal(relative_momentum=-0.10, rsi=35)
    assert sig1.triggered is False
    # RSI == 40 → 不觸發（要嚴格 < 40）
    sig2 = is_momentum_reversal(relative_momentum=-0.15, rsi=40)
    assert sig2.triggered is False
    # 雙邊界內側（-10.01%, 39.9）→ 觸發
    sig3 = is_momentum_reversal(relative_momentum=-0.1001, rsi=39.9)
    assert sig3.triggered is True


def test_thresholds_constants():
    """規格鎖定：-0.10 與 40"""
    assert MOMENTUM_GAP_THRESHOLD == -0.10
    assert RSI_OVERSOLD_THRESHOLD == 40
