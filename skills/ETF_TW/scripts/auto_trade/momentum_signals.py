"""
momentum_signals.py — 動能反轉賣訊（F1 計畫）

問題：sell_scanner 目前只有 trailing stop（peak_tracker），只回答「賺到要不要保住」，
      沒回答「**還沒賺夠但相對大盤跑輸要不要先跑**」。

設計：在 trailing 之外新增第二類賣訊。任一觸發即 enqueue（須過 ack）：

  動能反轉觸發條件（AND）：
    1. 個股近 20 日報酬 vs 大盤近 20 日報酬：個股跑輸 ≥ 10%
       （relative_momentum < -0.10）
    2. 當前 RSI < 40（弱勢，避免短期回檔誤判）

設計理由：
  - 不取代 trailing，是疊加（任一觸發 → enqueue sell signal）
  - 比 trailing 早出場，捕捉「還沒到 stop 但已經是該換馬的訊號」
  - RSI 條件防止短期回檔誤判（單靠相對動能會在大盤反彈時過早出場）

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 F1)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Constants — 由單元測試鎖定
# ---------------------------------------------------------------------------

MOMENTUM_GAP_THRESHOLD = -0.10   # 跑輸大盤 ≥ 10% 才視為弱勢
RSI_OVERSOLD_THRESHOLD = 40       # RSI < 40 才確認弱勢


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class MomentumSignal:
    """動能反轉訊號的回傳容器。"""
    triggered: bool
    relative_momentum: Optional[float]   # 個股 20d - 大盤 20d
    rsi: Optional[float]
    reason: str                           # 觸發或不觸發的原因


# ---------------------------------------------------------------------------
# 純函式
# ---------------------------------------------------------------------------

def compute_relative_momentum(
    *,
    symbol_return_20d: Optional[float],
    market_return_20d: Optional[float],
) -> Optional[float]:
    """
    個股 vs 大盤的相對 20 日報酬。

    Args:
        symbol_return_20d: 個股 20 日累積報酬率（小數，0.05 = +5%）
        market_return_20d: 大盤（^TWII）20 日累積報酬率
    Returns:
        相對報酬（symbol - market），或缺值時 None
    """
    if symbol_return_20d is None or market_return_20d is None:
        return None
    return float(symbol_return_20d) - float(market_return_20d)


def is_momentum_reversal(
    *,
    relative_momentum: Optional[float],
    rsi: Optional[float],
) -> MomentumSignal:
    """
    判斷是否觸發動能反轉賣訊。

    觸發條件（嚴格小於，AND 組合）：
      relative_momentum < -0.10  AND  rsi < 40
    """
    if relative_momentum is None or rsi is None:
        return MomentumSignal(
            triggered=False,
            relative_momentum=relative_momentum,
            rsi=rsi,
            reason="missing_data",
        )

    if relative_momentum >= MOMENTUM_GAP_THRESHOLD:
        return MomentumSignal(
            triggered=False,
            relative_momentum=relative_momentum,
            rsi=rsi,
            reason=f"underperform_threshold_not_met (gap={relative_momentum:.2%}, need<{MOMENTUM_GAP_THRESHOLD:.0%})",
        )

    if rsi >= RSI_OVERSOLD_THRESHOLD:
        return MomentumSignal(
            triggered=False,
            relative_momentum=relative_momentum,
            rsi=rsi,
            reason=f"rsi_too_strong (rsi={rsi:.1f}, need<{RSI_OVERSOLD_THRESHOLD})",
        )

    return MomentumSignal(
        triggered=True,
        relative_momentum=relative_momentum,
        rsi=rsi,
        reason="underperform_and_oversold",
    )
