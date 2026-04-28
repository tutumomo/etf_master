"""
strategy_simulator.py — 純函式回測核心

把 ETF_TW 的 ladder buy + trailing sell 規則放在歷史每日 OHLC 上模擬，回傳：
  - 完整交易序列 (Trade list)
  - 每日 equity_curve (pd.Series)
  - 績效指標 (compute_metrics)

設計原則：
  - 純函式：不讀檔、不寫檔、不打網路
  - 沿用 buy_scanner.ladder_amount 與 peak_tracker.GROUP_TRAILING_PCT 的數字
    （但不 import 它們以保持本檔測試獨立、可離線跑）
  - 一個交易日只做一次決策（簡化：用收盤價成交）
  - 整張限制：股數必須是 1000 的倍數
  - 手續費：買賣均 0.1425%；賣出再加 0.1% 證交稅

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 C)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 規則常數（與 scripts/auto_trade/buy_scanner.py & peak_tracker.py 同步）
# ---------------------------------------------------------------------------

# 買入階梯 — 骨架調整 v2（2026-04-29）
# v1：寫死 TWD 金額（2000-10000），與資金規模無關 → 部位永遠長不大
# v2：按可用現金的百分比計算，隨資金成長自動 scale
DROP_LADDER_PCT: list[tuple[float, float]] = [
    (-1.0, 0.005),   # 跌 1% → 投入 0.5% 現金
    (-2.0, 0.010),   # 跌 2% → 投入 1.0%
    (-3.0, 0.015),   # 跌 3% → 投入 1.5%
    (-4.0, 0.020),   # 跌 4% → 投入 2.0%
    (-5.0, 0.025),   # ≥ 5% → 投入 2.5%
]
# 保留舊常數供生產 buy_scanner 過渡期使用（會在後續 commit 同步調整）
DROP_LADDER: list[tuple[float, int]] = [
    (-1.0, 2000),
    (-2.0, 4000),
    (-3.0, 6000),
    (-4.0, 8000),
    (-5.0, 10000),
]
MIN_DROP_TO_TRIGGER = -1.0

# 賣出 trailing — 骨架調整 v2（2026-04-29）
# 原值（v1）：core 6 / income 5 / defensive 4 / growth 8 / smart_beta 7 / other 8
# 調整理由：C 計畫回測顯示 v1 太緊，部位無法累積，多頭時嚴重跟不上
GROUP_TRAILING_PCT: dict[str, float] = {
    "core":      0.12,  # 原 0.06
    "income":    0.10,  # 原 0.05
    "defensive": 0.08,  # 原 0.04
    "growth":    0.15,  # 原 0.08
    "smart_beta": 0.13, # 原 0.07
    "other":     0.15,  # 原 0.08
}
DEFAULT_TRAILING_PCT = 0.12  # 原 0.06
TRAIL_LOCK_PCT = 0.05        # 原 0.03（鎖利模式也放寬一點，避免一回檔就賣）
TRAIL_LOCK_THRESHOLD = 0.20

# 手續費
BROKER_FEE_RATE = 0.001425
SELL_TAX_RATE   = 0.001

LOT_SIZE = 1000  # 1 張 = 1000 股


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    date: str
    side: str       # 'buy' | 'sell'
    price: float
    shares: int
    cash_flow: float  # buy = -支出 (含 fee); sell = +收入 (扣除 fee)
    fee: float
    note: str = ""


@dataclass
class SimulationConfig:
    initial_cash: float
    symbol_group: str = "core"
    max_position_pct: float = 0.50  # 持倉最多佔總資產的比例（避免單一標的全押）
    use_lockin: bool = True
    custom_trailing_pct: Optional[float] = None  # 覆蓋 group default
    allow_odd_lot: bool = True  # ladder 金額不足 1 張時，是否允許 1-999 股（零股交易）

    # 骨架調整 v2：初始建倉（DCA 啟動）
    # initial_dca_target_pct = 0.5 表示「最多把 initial_cash 的 50% 用在初始建倉」
    # initial_dca_days = 20 表示分 20 個交易日完成
    # 設 0 → 關閉初始建倉（v1 行為）
    initial_dca_target_pct: float = 0.0
    initial_dca_days: int = 20


@dataclass
class SimulationResult:
    trades: list[Trade]
    equity_curve: object   # pd.Series (date → equity)
    final_equity: float
    initial_cash: float
    config: SimulationConfig
    label: str = ""        # 'strategy' / 'buy_and_hold'


# ---------------------------------------------------------------------------
# Pure rule functions
# ---------------------------------------------------------------------------

def ladder_amount(drop_pct: float, available_cash: Optional[float] = None) -> int:
    """跌幅 → 買入金額 (TWD)。drop_pct 為負值。沒跌夠 1% → 0。

    Args:
        drop_pct: 負值百分比（-2.5 表示跌 2.5%）
        available_cash: 若給定，按 DROP_LADDER_PCT 比例計算（v2 行為）；
                        若 None，回傳 DROP_LADDER 寫死金額（v1 相容）
    """
    drop_pct = round(drop_pct, 6)
    if drop_pct > MIN_DROP_TO_TRIGGER:
        return 0
    if available_cash is not None and available_cash > 0:
        for threshold, pct in reversed(DROP_LADDER_PCT):
            if drop_pct <= threshold:
                return int(available_cash * pct)
        return 0
    # v1 fallback：寫死 TWD
    for threshold, amount in reversed(DROP_LADDER):
        if drop_pct <= threshold:
            return amount
    return 0


def get_trailing_pct(group: str, return_pct: Optional[float] = None,
                     custom: Optional[float] = None) -> float:
    if custom is not None:
        return custom
    if return_pct is not None and return_pct >= TRAIL_LOCK_THRESHOLD:
        return TRAIL_LOCK_PCT
    return GROUP_TRAILING_PCT.get((group or "").lower(), DEFAULT_TRAILING_PCT)


def shares_from_amount(amount_twd: float, price: float, allow_odd_lot: bool = False) -> int:
    """TWD 金額 → 股數。
    allow_odd_lot=False：必須是 1000 的倍數，不足 1 張回 0
    allow_odd_lot=True ：先嘗試 1000 倍數，不足 1 張時退回 1-999 零股
    """
    if amount_twd <= 0 or price <= 0:
        return 0
    raw = int(amount_twd // price)
    lots = (raw // LOT_SIZE) * LOT_SIZE
    if lots > 0:
        return lots
    if allow_odd_lot and raw >= 1:
        return raw  # 零股：1-999 股
    return 0


# ---------------------------------------------------------------------------
# Simulation core
# ---------------------------------------------------------------------------

def simulate(prices, config: SimulationConfig) -> SimulationResult:
    """
    跑歷史模擬。

    Args:
        prices: pandas.DataFrame，需有 'Close' 欄，index 為日期
        config: SimulationConfig

    Returns:
        SimulationResult
    """
    import pandas as pd

    if prices is None or len(prices) == 0:
        empty_curve = pd.Series([], dtype=float)
        return SimulationResult(
            trades=[],
            equity_curve=empty_curve,
            final_equity=config.initial_cash,
            initial_cash=config.initial_cash,
            config=config,
            label="strategy",
        )

    cash = float(config.initial_cash)
    shares = 0
    avg_cost = 0.0
    peak_close = 0.0
    trades: list[Trade] = []
    equity_records: list[tuple[object, float]] = []

    closes = prices["Close"].astype(float)
    prev_close = None

    # === 初始建倉 (DCA 啟動) ===
    # 在前 N 個交易日，每日固定買入 initial_dca_total / N 的金額。
    # 這個邏輯會在 ladder 觸發之前執行；ladder 仍可在同一天疊加。
    dca_total = float(config.initial_cash) * float(config.initial_dca_target_pct or 0.0)
    dca_days_target = int(config.initial_dca_days or 0)
    dca_daily_amount = (dca_total / dca_days_target) if dca_days_target > 0 and dca_total > 0 else 0.0
    dca_days_done = 0

    for date, close in closes.items():
        date_str = str(date.date()) if hasattr(date, "date") else str(date)

        # === Initial DCA buy ===
        if dca_daily_amount > 0 and dca_days_done < dca_days_target and cash >= dca_daily_amount * 0.5:
            spend = min(dca_daily_amount, cash)
            dca_shares = shares_from_amount(spend, close, allow_odd_lot=config.allow_odd_lot)
            if dca_shares >= 1:
                cost = dca_shares * close
                fee = cost * BROKER_FEE_RATE
                total_out = cost + fee
                if cash >= total_out:
                    new_total_shares = shares + dca_shares
                    avg_cost = (avg_cost * shares + cost) / new_total_shares if new_total_shares > 0 else close
                    cash -= total_out
                    shares = new_total_shares
                    trades.append(Trade(
                        date=date_str, side="buy",
                        price=close, shares=dca_shares,
                        cash_flow=-total_out, fee=fee,
                        note=f"initial_dca day {dca_days_done + 1}/{dca_days_target}",
                    ))
                    peak_close = max(peak_close, close)
            dca_days_done += 1

        # === Buy logic ===
        if prev_close is not None:
            drop_pct = (close - prev_close) / prev_close * 100.0
            # v2: ladder 金額按目前可用現金比例
            buy_amount = ladder_amount(drop_pct, available_cash=cash)

            if buy_amount > 0:
                # 受 max_position_pct 限制
                total_equity_now = cash + shares * close
                current_position_value = shares * close
                max_allowed_position = total_equity_now * config.max_position_pct
                room_left = max(0.0, max_allowed_position - current_position_value)
                buy_amount = min(buy_amount, room_left, cash)

                buy_shares = shares_from_amount(buy_amount, close, allow_odd_lot=config.allow_odd_lot)
                if buy_shares >= 1:
                    cost = buy_shares * close
                    fee = cost * BROKER_FEE_RATE
                    total_out = cost + fee
                    if cash >= total_out:
                        # update avg_cost
                        new_total_shares = shares + buy_shares
                        avg_cost = (avg_cost * shares + cost) / new_total_shares
                        cash -= total_out
                        shares = new_total_shares
                        trades.append(Trade(
                            date=date_str, side="buy",
                            price=close, shares=buy_shares,
                            cash_flow=-total_out, fee=fee,
                            note=f"ladder drop_pct={drop_pct:.2f}%",
                        ))
                        # ladder 觸發後重設 peak（讓 trailing 從新 cost 起算 — 簡化）
                        peak_close = max(peak_close, close)

        # === Update peak ===
        if shares > 0:
            peak_close = max(peak_close, close)

            # === Trailing sell ===
            # v2: DCA 建倉期間不觸發 trailing（讓部位先建立起來，避免在初期被洗出場）
            in_dca_phase = dca_daily_amount > 0 and dca_days_done < dca_days_target
            return_pct = (close - avg_cost) / avg_cost if avg_cost > 0 else 0.0
            trailing_pct = get_trailing_pct(
                config.symbol_group,
                return_pct=return_pct if config.use_lockin else None,
                custom=config.custom_trailing_pct,
            )
            stop_price = peak_close * (1 - trailing_pct)
            if not in_dca_phase and close <= stop_price:
                proceeds = shares * close
                fee = proceeds * (BROKER_FEE_RATE + SELL_TAX_RATE)
                net = proceeds - fee
                trades.append(Trade(
                    date=date_str, side="sell",
                    price=close, shares=shares,
                    cash_flow=net, fee=fee,
                    note=f"trailing peak={peak_close:.2f} stop={stop_price:.2f} return={return_pct:.2%}",
                ))
                cash += net
                shares = 0
                avg_cost = 0.0
                peak_close = 0.0

        # Record equity at end of day
        equity_records.append((date, cash + shares * close))
        prev_close = close

    equity_curve = pd.Series(
        [e for _, e in equity_records],
        index=[d for d, _ in equity_records],
        name="equity",
    )

    return SimulationResult(
        trades=trades,
        equity_curve=equity_curve,
        final_equity=float(equity_curve.iloc[-1]) if len(equity_curve) > 0 else cash,
        initial_cash=config.initial_cash,
        config=config,
        label="strategy",
    )


def simulate_buy_and_hold(prices, initial_cash: float, *, allow_odd_lot: bool = True) -> SimulationResult:
    """對照組：第一天買進、最後一天賣出。

    allow_odd_lot 預設 True，因為對照組要能在 ^TWII 這種指數標的上產生有意義的對照
    （指數點位 8000+ 時 1M TWD 連 1 張都不夠）。
    """
    import pandas as pd

    if prices is None or len(prices) == 0:
        return SimulationResult(
            trades=[],
            equity_curve=pd.Series([], dtype=float),
            final_equity=initial_cash,
            initial_cash=initial_cash,
            config=SimulationConfig(initial_cash=initial_cash, symbol_group="bah"),
            label="buy_and_hold",
        )

    cfg = SimulationConfig(initial_cash=initial_cash, symbol_group="bah")
    closes = prices["Close"].astype(float)
    first_price = float(closes.iloc[0])

    # Day 1 buy as much as possible
    buy_shares = shares_from_amount(initial_cash, first_price, allow_odd_lot=allow_odd_lot)
    cost = buy_shares * first_price
    buy_fee = cost * BROKER_FEE_RATE
    cash = initial_cash - cost - buy_fee
    trades: list[Trade] = []
    if buy_shares > 0:
        trades.append(Trade(
            date=str(closes.index[0].date()) if hasattr(closes.index[0], "date") else str(closes.index[0]),
            side="buy", price=first_price, shares=buy_shares,
            cash_flow=-(cost + buy_fee), fee=buy_fee,
            note="buy_and_hold initial",
        ))

    # Equity curve: cash + shares × close
    equity = cash + buy_shares * closes
    equity.name = "equity"

    # Sell on last day
    last_price = float(closes.iloc[-1])
    proceeds = buy_shares * last_price
    sell_fee = proceeds * (BROKER_FEE_RATE + SELL_TAX_RATE)
    net = proceeds - sell_fee
    if buy_shares > 0:
        trades.append(Trade(
            date=str(closes.index[-1].date()) if hasattr(closes.index[-1], "date") else str(closes.index[-1]),
            side="sell", price=last_price, shares=buy_shares,
            cash_flow=net, fee=sell_fee,
            note="buy_and_hold final",
        ))
    final_equity = cash + net
    # Replace last equity with post-sell value
    if len(equity) > 0:
        equity.iloc[-1] = final_equity

    return SimulationResult(
        trades=trades,
        equity_curve=equity,
        final_equity=final_equity,
        initial_cash=initial_cash,
        config=cfg,
        label="buy_and_hold",
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(equity_curve) -> dict:
    """從 equity curve 計算績效指標。"""
    import pandas as pd
    import numpy as np

    if equity_curve is None or len(equity_curve) == 0:
        return {
            "total_return_pct": None,
            "max_drawdown_pct": None,
            "sharpe_ratio": None,
            "max_consecutive_loss_days": None,
            "annualized_return_pct": None,
            "annualized_volatility_pct": None,
        }

    eq = pd.Series(equity_curve).astype(float)
    initial = float(eq.iloc[0])
    final = float(eq.iloc[-1])
    total_return = (final - initial) / initial * 100.0

    # Max drawdown
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max * 100.0
    max_dd = float(drawdown.min())

    # Daily returns
    returns = eq.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe = float(returns.mean() / returns.std() * np.sqrt(252))
    else:
        sharpe = 0.0

    # Annualized
    n_days = len(eq)
    if n_days > 0:
        years = n_days / 252.0
        if years > 0 and initial > 0 and final > 0:
            annualized_return = ((final / initial) ** (1.0 / years) - 1.0) * 100.0
        else:
            annualized_return = 0.0
        annualized_vol = float(returns.std() * np.sqrt(252) * 100.0) if len(returns) > 1 else 0.0
    else:
        annualized_return = 0.0
        annualized_vol = 0.0

    # Max consecutive loss days
    diffs = eq.diff()
    max_streak = 0
    cur_streak = 0
    for d in diffs:
        if pd.notna(d) and d < 0:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0

    return {
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_consecutive_loss_days": max_streak,
        "annualized_return_pct": round(annualized_return, 2),
        "annualized_volatility_pct": round(annualized_vol, 2),
    }
