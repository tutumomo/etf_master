"""
Tests for auto_trade.macro_regime_signals:
  - compute_twii_vs_200ma: 偏離百分比
  - compute_60d_percentile: 60 日價格百分位
  - compute_macro_score: 三訊號融合 -3 ~ +3
  - 邊界：資料缺失 / 資料不足 / 全部正常
"""
from datetime import datetime, timedelta, timezone

import pytest

pd = pytest.importorskip("pandas")
import numpy as np

from scripts.auto_trade.macro_regime_signals import (
    compute_twii_vs_200ma,
    compute_60d_percentile,
    compute_macro_score,
    MacroSignals,
    classify_macro_regime,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_history(prices: list[float]) -> pd.DataFrame:
    """造一個 yfinance 風格的 history DataFrame，index 是遞增日期。"""
    n = len(prices)
    end = datetime(2026, 4, 28, tzinfo=timezone.utc)
    idx = pd.DatetimeIndex([end - timedelta(days=n - 1 - i) for i in range(n)])
    return pd.DataFrame({
        "Open":  prices,
        "High":  [p * 1.01 for p in prices],
        "Low":   [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [1_000_000] * n,
    }, index=idx)


# ---------------------------------------------------------------------------
# compute_twii_vs_200ma
# ---------------------------------------------------------------------------

def test_twii_vs_200ma_above():
    """收盤 > 200MA → 正百分比"""
    prices = [100.0] * 200 + [110.0]
    df = _make_history(prices)
    result = compute_twii_vs_200ma(df)
    # 200MA ≈ (199*100 + 110)/200 ≈ 100.05; current=110 → +9.95%
    assert result is not None
    assert 9.0 < result < 11.0


def test_twii_vs_200ma_below():
    """收盤 < 200MA → 負百分比"""
    prices = [100.0] * 200 + [90.0]
    df = _make_history(prices)
    result = compute_twii_vs_200ma(df)
    assert result is not None
    assert -11.0 < result < -9.0


def test_twii_vs_200ma_at_ma():
    prices = [100.0] * 201
    df = _make_history(prices)
    result = compute_twii_vs_200ma(df)
    assert result is not None
    assert abs(result) < 0.01


def test_twii_vs_200ma_insufficient_data():
    """少於 200 筆 → None"""
    df = _make_history([100.0] * 50)
    assert compute_twii_vs_200ma(df) is None


def test_twii_vs_200ma_empty():
    assert compute_twii_vs_200ma(pd.DataFrame()) is None
    assert compute_twii_vs_200ma(None) is None


# ---------------------------------------------------------------------------
# compute_60d_percentile
# ---------------------------------------------------------------------------

def test_60d_percentile_at_top():
    """current price 是過去 60 日最高 → 100%"""
    prices = list(range(60, 121))  # 61 prices, last is highest
    df = _make_history(prices)
    pct = compute_60d_percentile(df)
    assert pct is not None
    assert pct >= 95.0


def test_60d_percentile_at_bottom():
    """current price 是過去 60 日最低"""
    prices = list(range(120, 60, -1))  # decreasing → last is lowest
    df = _make_history(prices)
    pct = compute_60d_percentile(df)
    assert pct is not None
    assert pct <= 5.0


def test_60d_percentile_middle():
    prices = [100.0] * 30 + [90.0] * 30 + [95.0]
    df = _make_history(prices)
    pct = compute_60d_percentile(df)
    assert pct is not None
    # 95 處於 90 和 100 中間 → 大約 50%
    assert 40.0 <= pct <= 60.0


def test_60d_percentile_insufficient_data():
    df = _make_history([100.0] * 30)
    assert compute_60d_percentile(df) is None


def test_60d_percentile_empty():
    assert compute_60d_percentile(pd.DataFrame()) is None


# ---------------------------------------------------------------------------
# compute_macro_score
# ---------------------------------------------------------------------------

def test_macro_score_all_bullish():
    """大盤強、VIX 低、百分位高 → +3"""
    sig = MacroSignals(twii_vs_200ma_pct=8.0, vix=15.0, twii_60d_percentile=85.0)
    assert compute_macro_score(sig) == 3


def test_macro_score_all_bearish():
    """大盤弱、VIX 高、百分位低 → -3"""
    sig = MacroSignals(twii_vs_200ma_pct=-8.0, vix=35.0, twii_60d_percentile=15.0)
    assert compute_macro_score(sig) == -3


def test_macro_score_mixed():
    """偏離 0、VIX 中等、百分位中等 → 0"""
    sig = MacroSignals(twii_vs_200ma_pct=0.5, vix=22.0, twii_60d_percentile=50.0)
    assert compute_macro_score(sig) == 0


def test_macro_score_partial_data():
    """缺 VIX，仍可從另兩訊號算出 -2 ~ +2 範圍"""
    sig = MacroSignals(twii_vs_200ma_pct=8.0, vix=None, twii_60d_percentile=85.0)
    score = compute_macro_score(sig)
    assert score == 2  # 最高就 +2，VIX 沒貢獻


def test_macro_score_no_data():
    sig = MacroSignals(twii_vs_200ma_pct=None, vix=None, twii_60d_percentile=None)
    assert compute_macro_score(sig) == 0  # 中性


def test_macro_score_thresholds_above_200ma():
    """規則：>25%→-1(過熱), 5<x<=25%→+1, [-5,5]→0, <-5%→-1"""
    assert compute_macro_score(MacroSignals(5.1, 22, 50)) == 1
    assert compute_macro_score(MacroSignals(25.0, 22, 50)) == 1   # 邊界內仍 +1
    assert compute_macro_score(MacroSignals(-5.1, 22, 50)) == -1
    assert compute_macro_score(MacroSignals(4.9, 22, 50)) == 0


def test_macro_score_overheat_penalty():
    """偏離 200MA > +25% 觸發 mean-reversion 警示，從 +1 翻轉為 -1"""
    # +38% 過熱（對應 2024 末/2026 初台股實況）
    overheat = MacroSignals(38.0, 18.0, 96.0)
    # twii: -1 (過熱), vix<20: +1, percentile>70: +1 → total +1
    assert compute_macro_score(overheat) == 1
    # 同樣 percentile/vix 但偏離 +20%（健康牛市）→ +3
    healthy_bull = MacroSignals(20.0, 18.0, 96.0)
    assert compute_macro_score(healthy_bull) == 3
    # 邊界精確值：+25% 仍 +1
    assert compute_macro_score(MacroSignals(25.0, 22, 50)) == 1
    # +25.01% 翻為 -1
    assert compute_macro_score(MacroSignals(25.01, 22, 50)) == -1


def test_classify_overheat_is_not_bullish():
    """+38% 過熱情境不應分類為 macro_bullish"""
    sig = MacroSignals(38.0, 18.0, 96.0)
    label = classify_macro_regime(sig)
    assert label != "macro_bullish"  # score=+1 → macro_neutral


def test_macro_score_thresholds_vix():
    """>30→-1, <20→+1, [20,30]→0"""
    assert compute_macro_score(MacroSignals(0, 31, 50)) == -1
    assert compute_macro_score(MacroSignals(0, 19, 50)) == 1
    assert compute_macro_score(MacroSignals(0, 25, 50)) == 0


def test_macro_score_thresholds_percentile():
    """>70→+1, <30→-1, [30,70]→0"""
    assert compute_macro_score(MacroSignals(0, 22, 71)) == 1
    assert compute_macro_score(MacroSignals(0, 22, 29)) == -1
    assert compute_macro_score(MacroSignals(0, 22, 50)) == 0


# ---------------------------------------------------------------------------
# classify_macro_regime — 高階對映
# ---------------------------------------------------------------------------

def test_classify_macro_bullish():
    sig = MacroSignals(8.0, 15.0, 85.0)
    label = classify_macro_regime(sig)
    assert label == "macro_bullish"


def test_classify_macro_cautious():
    sig = MacroSignals(-8.0, 35.0, 15.0)
    label = classify_macro_regime(sig)
    assert label == "macro_cautious"


def test_classify_macro_neutral():
    sig = MacroSignals(0.5, 22.0, 50.0)
    label = classify_macro_regime(sig)
    assert label == "macro_neutral"
