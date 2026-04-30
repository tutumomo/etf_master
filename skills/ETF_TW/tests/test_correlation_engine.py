"""
Tests for auto_trade.correlation_engine:
  - compute_pairwise_correlation: 純函式，由日報酬序列算 N×N 相關矩陣
  - compute_avg_correlation_with_holdings: 候選 vs 既有持倉的平均相關
  - apply_correlation_penalty: 依平均相關回傳 0.2~1.0 的 multiplier
  - 邊界：空持倉、單一持倉、相關性異常值
"""
from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
import numpy as np

from scripts.auto_trade.correlation_engine import (
    CorrelationMatrix,
    compute_pairwise_correlation,
    compute_avg_correlation_with_holdings,
    apply_correlation_penalty,
    CORRELATION_THRESHOLD,
    PENALTY_FLOOR,
)


# ---------------------------------------------------------------------------
# compute_pairwise_correlation
# ---------------------------------------------------------------------------

def test_pairwise_correlation_perfectly_correlated():
    """兩檔報酬完全相同 → corr = 1.0"""
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, -0.01, 0.02, -0.005, 0.015, 0.0, -0.01, 0.02],
        "B": [0.01, -0.02, 0.03, -0.01, 0.02, -0.005, 0.015, 0.0, -0.01, 0.02],
    })
    cm = compute_pairwise_correlation(returns)
    assert cm.matrix.loc["A", "B"] == pytest.approx(1.0)
    assert cm.matrix.loc["A", "A"] == pytest.approx(1.0)


def test_pairwise_correlation_anti_correlated():
    """完全反向 → corr = -1.0"""
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, -0.01, 0.02, -0.005, 0.015, 0.0, -0.01, 0.02],
        "B": [-0.01, 0.02, -0.03, 0.01, -0.02, 0.005, -0.015, 0.0, 0.01, -0.02],
    })
    cm = compute_pairwise_correlation(returns)
    assert cm.matrix.loc["A", "B"] == pytest.approx(-1.0, abs=0.01)


def test_pairwise_correlation_uncorrelated():
    """近乎獨立 → corr 接近 0"""
    np.random.seed(42)
    returns = pd.DataFrame({
        "A": np.random.randn(100) * 0.01,
        "B": np.random.randn(100) * 0.01,
    })
    cm = compute_pairwise_correlation(returns)
    assert abs(cm.matrix.loc["A", "B"]) < 0.3  # 隨機應該相關度低


def test_pairwise_correlation_lookup():
    """get(symbol_a, symbol_b) 應對稱"""
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, -0.01, 0.02, -0.005, 0.015],
        "B": [0.005, -0.01, 0.02, 0.0, 0.01, -0.005, 0.01],
    })
    cm = compute_pairwise_correlation(returns)
    ab = cm.get("A", "B")
    ba = cm.get("B", "A")
    assert ab == ba
    assert -1.0 <= ab <= 1.0


def test_pairwise_correlation_missing_symbol():
    """查不到的 symbol 應回 None"""
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.0], "B": [0.0, 0.01, -0.01]})
    cm = compute_pairwise_correlation(returns)
    assert cm.get("A", "Z") is None
    assert cm.get("X", "Y") is None


def test_pairwise_correlation_empty_input():
    cm = compute_pairwise_correlation(pd.DataFrame())
    assert cm.symbols == []


def test_pairwise_correlation_single_symbol():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03, -0.01, 0.02]})
    cm = compute_pairwise_correlation(returns)
    # 單一 symbol：自相關 = 1，其他查無
    assert cm.matrix.loc["A", "A"] == pytest.approx(1.0)
    assert cm.get("A", "B") is None


# ---------------------------------------------------------------------------
# compute_avg_correlation_with_holdings
# ---------------------------------------------------------------------------

def test_avg_corr_no_holdings_returns_none():
    """空持倉 → None（沒有既有 bet 可疊加）"""
    returns = pd.DataFrame({"A": [0.01, -0.01], "B": [0.0, 0.01]})
    cm = compute_pairwise_correlation(returns)
    assert compute_avg_correlation_with_holdings(cm, candidate="A", holdings=[]) is None


def test_avg_corr_self_holding_excluded():
    """已持有 candidate 自己，不算進平均（自相關=1 會扭曲結果）"""
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, -0.01, 0.02],
        "B": [0.005, -0.01, 0.015, -0.005, 0.01],  # 與 A 高相關
    })
    cm = compute_pairwise_correlation(returns)
    avg = compute_avg_correlation_with_holdings(cm, candidate="A", holdings=["A", "B"])
    # 排除 A 自己，只剩 corr(A, B)
    assert avg == pytest.approx(cm.get("A", "B"))


def test_avg_corr_multiple_holdings():
    """多檔持倉 → 平均"""
    returns = pd.DataFrame({
        "X": [0.01, -0.02, 0.03, -0.01, 0.02],
        "Y": [0.005, -0.015, 0.025, -0.005, 0.018],   # 與 X 略相關
        "Z": [-0.005, 0.01, -0.02, 0.005, -0.015],    # 與 X 反向
    })
    cm = compute_pairwise_correlation(returns)
    avg = compute_avg_correlation_with_holdings(cm, candidate="X", holdings=["Y", "Z"])
    expected = (cm.get("X", "Y") + cm.get("X", "Z")) / 2
    assert avg == pytest.approx(expected)


def test_avg_corr_unknown_candidate_returns_none():
    """candidate 不在矩陣裡 → None（無法判斷）"""
    returns = pd.DataFrame({"A": [0.01, -0.01], "B": [0.0, 0.01]})
    cm = compute_pairwise_correlation(returns)
    assert compute_avg_correlation_with_holdings(cm, candidate="Z", holdings=["A", "B"]) is None


def test_avg_corr_holdings_not_in_matrix_skipped():
    """持倉裡有些 symbol 不在矩陣裡，跳過不算"""
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.03, -0.01, 0.02],
        "B": [0.005, -0.01, 0.015, -0.005, 0.01],
    })
    cm = compute_pairwise_correlation(returns)
    # 持倉裡 Q 不在矩陣 → 只算 A vs B
    avg = compute_avg_correlation_with_holdings(cm, candidate="A", holdings=["B", "Q"])
    assert avg == pytest.approx(cm.get("A", "B"))


# ---------------------------------------------------------------------------
# apply_correlation_penalty
# ---------------------------------------------------------------------------

def test_penalty_no_corr_full_amount():
    """avg_corr <= 0.7 → multiplier = 1.0（不折扣）"""
    assert apply_correlation_penalty(0.5) == pytest.approx(1.0)
    assert apply_correlation_penalty(0.3) == pytest.approx(1.0)
    assert apply_correlation_penalty(-0.2) == pytest.approx(1.0)


def test_penalty_at_threshold():
    """avg_corr 剛好 0.7 → 不折扣（threshold 是嚴格 >）"""
    assert apply_correlation_penalty(0.7) == pytest.approx(1.0)


def test_penalty_high_corr():
    """avg_corr > 0.7 → 1 - corr，但 floor 0.2"""
    # 0.85 → 1 - 0.85 = 0.15 → 提升至 floor 0.2
    assert apply_correlation_penalty(0.85) == pytest.approx(PENALTY_FLOOR)
    # 0.75 → 1 - 0.75 = 0.25 → 高於 floor，回傳 0.25
    assert apply_correlation_penalty(0.75) == pytest.approx(0.25)
    # 0.95 → 0.05 → 提升至 floor
    assert apply_correlation_penalty(0.95) == pytest.approx(PENALTY_FLOOR)


def test_penalty_perfect_corr():
    """avg_corr = 1.0 → multiplier = floor"""
    assert apply_correlation_penalty(1.0) == pytest.approx(PENALTY_FLOOR)


def test_penalty_none_avg_corr_full_amount():
    """avg_corr = None（空持倉或無資料）→ multiplier = 1.0（不折扣）"""
    assert apply_correlation_penalty(None) == pytest.approx(1.0)


def test_penalty_threshold_constants():
    """規格鎖定：threshold=0.7、floor=0.2"""
    assert CORRELATION_THRESHOLD == 0.7
    assert PENALTY_FLOOR == 0.2
