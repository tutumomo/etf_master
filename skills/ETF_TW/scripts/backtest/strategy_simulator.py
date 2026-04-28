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

# 買入階梯：跌幅 → 金額 (TWD)
DROP_LADDER: list[tuple[float, int]] = [
    (-1.0, 2000),
    (-2.0, 4000),
    (-3.0, 6000),
    (-4.0, 8000),
    (-5.0, 10000),
]
MIN_DROP_TO_TRIGGER = -1.0

# 賣出 trailing
GROUP_TRAILING_PCT: dict[str, float] = {
    "core":      0.06,
    "income":    0.05,
    "defensive": 0.04,
    "growth":    0.08,
    "smart_beta": 0.07,
    "other":     0.08,
}
DEFAULT_TRAILING_PCT = 0.06
TRAIL_LOCK_PCT = 0.03
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

def ladder_amount(drop_pct: float) -> int:
    """跌幅 → 買入金額 (TWD)。drop_pct 為負值。沒跌夠 1% → 0。"""
    drop_pct = round(drop_pct, 6)
    if drop_pct > MIN_DROP_TO_TRIGGER:
        return 0
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

    for date, close in closes.items():
        date_str = str(date.date()) if hasattr(date, "date") else str(date)

        # === Buy logic ===
        if prev_close is not None:
            drop_pct = (close - prev_close) / prev_close * 100.0
            buy_amount = ladder_amount(drop_pct)

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
            return_pct = (close - avg_cost) / avg_cost if avg_cost > 0 else 0.0
            trailing_pct = get_trailing_pct(
                config.symbol_group,
                return_pct=return_pct if config.use_lockin else None,
                custom=config.custom_trailing_pct,
            )
            stop_price = peak_close * (1 - trailing_pct)
            if close <= stop_price:
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
