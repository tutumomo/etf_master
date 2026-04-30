"""
correlation_engine.py — 持倉相關性懲罰（E2 計畫）

問題：watchlist 中多檔高度相關的 ETF 等於同一 bet：
  - 高股息群（0056 / 00878 / 00919 / 00713 / 00929）相關 >0.8
  - 美債群（00679B / 00687B）相關 >0.95
  - 大盤群（0050 / 006208）相關 >0.99

買第二檔同類就是「重複押注」。E2 在買進時計算「擬買標的 vs 既有持倉」
平均相關，>0.7 → 倉位線性折扣，floor 0.2 防止完全歸零。

設計原則：
  - 純函式，可離線測試（不打 yfinance）
  - 上層腳本（compute_correlation_matrix.py）負責週期性更新
    state/correlation_matrix.json，本模組只讀取與計算

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 E2)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants — 由單元測試鎖定
# ---------------------------------------------------------------------------

CORRELATION_THRESHOLD = 0.7   # 平均相關 > 此值才啟動折扣
PENALTY_FLOOR = 0.2            # multiplier 最低 0.2，避免完全歸零


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class CorrelationMatrix:
    """N×N pairwise correlation matrix 的容器。"""
    matrix: object  # pd.DataFrame
    symbols: list[str] = field(default_factory=list)

    def get(self, sym_a: str, sym_b: str) -> Optional[float]:
        """查 (sym_a, sym_b) 的相關係數；查無 → None。"""
        if self.matrix is None:
            return None
        try:
            if sym_a not in self.matrix.index or sym_b not in self.matrix.columns:
                return None
            val = self.matrix.loc[sym_a, sym_b]
            return float(val)
        except (KeyError, ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# 純函式：相關矩陣計算
# ---------------------------------------------------------------------------

def compute_pairwise_correlation(returns) -> CorrelationMatrix:
    """
    從 daily returns DataFrame 計算 pairwise 相關矩陣。

    Args:
        returns: pandas DataFrame，columns 是 symbol，每 row 是一日報酬率

    Returns:
        CorrelationMatrix
    """
    import pandas as pd

    if returns is None or len(returns) == 0 or len(returns.columns) == 0:
        return CorrelationMatrix(matrix=pd.DataFrame(), symbols=[])

    matrix = returns.corr()
    return CorrelationMatrix(matrix=matrix, symbols=list(matrix.columns))


# ---------------------------------------------------------------------------
# 應用：候選 vs 持倉的平均相關
# ---------------------------------------------------------------------------

def compute_avg_correlation_with_holdings(
    cm: CorrelationMatrix,
    *,
    candidate: str,
    holdings: list[str],
) -> Optional[float]:
    """
    計算候選 symbol 與既有持倉的平均相關係數。

    規則：
      - holdings 為空 → None（沒有既有 bet 可疊加，不需懲罰）
      - candidate 自己若也在 holdings → 排除（避免自相關 = 1 扭曲）
      - holdings 中不在矩陣裡的 symbol → 跳過
      - 全部跳過後沒有可用 pair → None

    Returns:
        平均相關係數（-1.0 ~ 1.0），或 None
    """
    if not holdings:
        return None
    if cm is None or cm.get(candidate, candidate) is None:
        # candidate 不在矩陣裡 → 無法判斷
        return None

    corrs: list[float] = []
    for h in holdings:
        if h == candidate:
            continue
        c = cm.get(candidate, h)
        if c is not None:
            corrs.append(c)

    if not corrs:
        return None
    return sum(corrs) / len(corrs)


# ---------------------------------------------------------------------------
# 應用：折扣 multiplier
# ---------------------------------------------------------------------------

def apply_correlation_penalty(avg_corr: Optional[float]) -> float:
    """
    依平均相關回傳 multiplier (0.2 ~ 1.0)。

    規則：
      avg_corr is None         → 1.0（不折扣）
      avg_corr <= THRESHOLD     → 1.0（不折扣）
      avg_corr > THRESHOLD      → max(FLOOR, 1 - avg_corr)
    """
    if avg_corr is None:
        return 1.0
    if avg_corr <= CORRELATION_THRESHOLD:
        return 1.0
    raw_multiplier = 1.0 - float(avg_corr)
    return max(PENALTY_FLOOR, raw_multiplier)


# ---------------------------------------------------------------------------
# 整合：給 buy_scanner 的便利函式
# ---------------------------------------------------------------------------

def compute_penalty_for_candidate(
    cm: Optional[CorrelationMatrix],
    *,
    candidate: str,
    holdings: list[str],
) -> dict:
    """
    一站式函式：給 buy_scanner 用。
    回傳 {avg_corr, multiplier, penalty_applied: bool, reason}。
    """
    if cm is None or not getattr(cm, "symbols", None):
        return {
            "avg_corr": None, "multiplier": 1.0,
            "penalty_applied": False, "reason": "no_matrix",
        }
    avg = compute_avg_correlation_with_holdings(cm, candidate=candidate, holdings=holdings)
    mult = apply_correlation_penalty(avg)
    return {
        "avg_corr": avg,
        "multiplier": mult,
        "penalty_applied": mult < 1.0,
        "reason": (
            "no_holdings" if not holdings
            else "candidate_not_in_matrix" if avg is None
            else "below_threshold" if avg <= CORRELATION_THRESHOLD
            else "high_correlation"
        ),
    }
