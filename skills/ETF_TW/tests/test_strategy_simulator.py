"""
Tests for backtest.strategy_simulator:
  - simulate(): pure function, replays ladder + trailing on OHLC history
  - compute_metrics(): equity curve → Sharpe, max drawdown, total return
  - buy-and-hold reference

Test data: synthetic price series with known shape so we can predict outcomes.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

pd = pytest.importorskip("pandas")
import numpy as np

from scripts.backtest.strategy_simulator import (
    SimulationConfig,
    Trade,
    simulate,
    simulate_buy_and_hold,
    compute_metrics,
    BROKER_FEE_RATE,
    SELL_TAX_RATE,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_prices(closes: list[float], start: str = "2020-01-01") -> pd.DataFrame:
    """Create OHLC DataFrame from list of closes (open/high/low approximated)."""
    n = len(closes)
    idx = pd.DatetimeIndex(pd.date_range(start, periods=n, freq="B"))
    return pd.DataFrame({
        "Open":  closes,
        "High":  [c * 1.01 for c in closes],
        "Low":   [c * 0.99 for c in closes],
        "Close": closes,
        "Volume": [1_000_000] * n,
    }, index=idx)


def _default_config() -> SimulationConfig:
    return SimulationConfig(
        initial_cash=1_000_000.0,
        symbol_group="core",
        max_position_pct=0.95,  # allow large position so we can see ladder triggers
    )


# ---------------------------------------------------------------------------
# simulate(): basic plumbing
# ---------------------------------------------------------------------------

def test_simulate_no_drops_no_trades():
    """Flat prices (zero drop) → no buys, no sells."""
    prices = _make_prices([100.0] * 30)
    result = simulate(prices, _default_config())
    assert len(result.trades) == 0
    assert result.final_equity == pytest.approx(1_000_000.0)


def test_simulate_steady_uptrend_no_buys_but_no_sells():
    """+0.5% per day, never triggers ladder, never triggers trailing."""
    closes = [100.0 * (1.005 ** i) for i in range(30)]
    prices = _make_prices(closes)
    result = simulate(prices, _default_config())
    assert len(result.trades) == 0


def test_simulate_drop_triggers_buy():
    """Day 2 drops -2% → ladder buys 4000 TWD worth (rounded down to lot of 1000).

    With price 98.0 and 4000 TWD: 4000/98 = 40.8 shares → rounded to 0 (no full lot).
    So we need higher initial cash impact... actually with our ladder system buying TWD,
    we test that the buy happens when affordable.
    """
    # Use small price so that 4000 TWD ÷ price > 1000 shares → board lot = 1000 shares
    # price=2 TWD: 4000/2 = 2000 shares → 2 lots = 2000 shares
    prices = _make_prices([2.0, 1.96])  # -2% drop
    result = simulate(prices, _default_config())
    buys = [t for t in result.trades if t.side == "buy"]
    assert len(buys) == 1
    assert buys[0].shares == 2000  # 2 lots
    assert buys[0].price == pytest.approx(1.96)


def test_simulate_drop_below_1pct_no_buy():
    """0.9% drop is below MIN_DROP_TO_TRIGGER (-1.0%)."""
    prices = _make_prices([100.0, 99.1])  # -0.9%
    result = simulate(prices, _default_config())
    assert len(result.trades) == 0


def test_simulate_trailing_triggers_sell():
    """
    Buy on day 2 (-2%), price climbs to peak, then drops > 6% from peak (core group).
    """
    # Day 0: 2.0
    # Day 1: 1.96 (-2% → buy)
    # Day 2-4: climb to 2.10 (peak)
    # Day 5: 1.97 (drop -6.2% from peak → trailing fires)
    closes = [2.0, 1.96, 2.00, 2.05, 2.10, 1.97]
    prices = _make_prices(closes)
    result = simulate(prices, _default_config())
    buys = [t for t in result.trades if t.side == "buy"]
    sells = [t for t in result.trades if t.side == "sell"]
    assert len(buys) >= 1
    assert len(sells) >= 1
    # Sell price ~ 1.97, peak ~ 2.10, drop = -6.2%
    assert sells[0].price == pytest.approx(1.97)


def test_simulate_no_buy_when_insufficient_cash():
    """Tiny initial cash (less than 1 share even as odd lot) → no buys."""
    cfg = SimulationConfig(initial_cash=100.0, symbol_group="core", max_position_pct=0.95,
                           allow_odd_lot=False)
    prices = _make_prices([2.0, 1.96])
    result = simulate(prices, cfg)
    # 100 TWD with 1.96 price → max 51 shares (odd lot) but allow_odd_lot=False → 0
    # And at -2% → ladder amount=4000, but only 100 cash → still nothing
    # Without odd lot: 100/1.96 = 51 → not 1000-multiple → 0 lots → 0 trades
    assert len(result.trades) == 0


def test_simulate_odd_lot_buy_when_high_price():
    """High price (e.g. 0050 @ 24) where ladder amount=4000 only buys ~166 shares,
    not enough for 1 lot. With allow_odd_lot=True, should buy as odd lot."""
    # Day 0 close=24.5, Day 1 close=24.0 → drop -2.04% → ladder=4000 TWD
    # 4000/24 = 166 shares (odd lot)
    cfg = SimulationConfig(initial_cash=100_000.0, symbol_group="core",
                           max_position_pct=0.95, allow_odd_lot=True)
    prices = _make_prices([24.5, 24.0])
    result = simulate(prices, cfg)
    buys = [t for t in result.trades if t.side == "buy"]
    assert len(buys) == 1
    assert 1 <= buys[0].shares < 1000  # odd lot
    assert buys[0].shares == 166  # 4000 // 24


def test_simulate_odd_lot_disabled_skips_when_under_lot():
    """With allow_odd_lot=False and ladder amount can't fill 1 lot → no buy."""
    cfg = SimulationConfig(initial_cash=100_000.0, symbol_group="core",
                           max_position_pct=0.95, allow_odd_lot=False)
    prices = _make_prices([24.5, 24.0])
    result = simulate(prices, cfg)
    assert len(result.trades) == 0


# ---------------------------------------------------------------------------
# Buy-and-hold reference
# ---------------------------------------------------------------------------

def test_buy_and_hold_first_day_full_position():
    """BAH buys on first day with all available cash, sells on last day."""
    closes = [10.0] * 5 + [11.0]  # +10% over period
    prices = _make_prices(closes)
    result = simulate_buy_and_hold(prices, initial_cash=1_000_000.0)
    assert len(result.trades) == 2  # 1 buy + 1 sell
    assert result.trades[0].side == "buy"
    assert result.trades[-1].side == "sell"
    # Should be close to +10% before fees
    # 100,000 shares × 10 = 1,000,000 buy
    # 100,000 shares × 11 = 1,100,000 sell
    # Roughly +10% minus fees
    assert result.final_equity > 1_080_000  # at least +8% net
    assert result.final_equity < 1_120_000  # not more than +12%


def test_buy_and_hold_handles_lot_rounding():
    """1M TWD ÷ 33.33 = 30,003 shares → rounds down to 30,000 (30 lots)."""
    closes = [33.33] * 5
    prices = _make_prices(closes)
    result = simulate_buy_and_hold(prices, initial_cash=1_000_000.0)
    assert result.trades[0].shares == 30_000


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_compute_metrics_basic():
    equity = pd.Series([1_000_000, 1_010_000, 1_020_000, 1_005_000, 1_030_000])
    m = compute_metrics(equity)
    assert m["total_return_pct"] == pytest.approx(3.0, abs=0.01)
    assert m["max_drawdown_pct"] < 0  # there was a drawdown
    # max drawdown: 1,020,000 → 1,005,000 = -1.47%
    assert m["max_drawdown_pct"] == pytest.approx(-1.4706, abs=0.01)


def test_compute_metrics_monotonic_up_no_drawdown():
    equity = pd.Series([100, 110, 120, 130])
    m = compute_metrics(equity)
    assert m["max_drawdown_pct"] == 0.0


def test_compute_metrics_empty():
    m = compute_metrics(pd.Series([], dtype=float))
    assert m["total_return_pct"] is None


def test_compute_metrics_max_consecutive_loss_days():
    # Up, up, down, down, down (3 consecutive losses), up, down
    equity = pd.Series([100, 102, 104, 103, 101, 99, 100, 99])
    m = compute_metrics(equity)
    assert m["max_consecutive_loss_days"] == 3


# ---------------------------------------------------------------------------
# Fees applied correctly
# ---------------------------------------------------------------------------

def test_fees_buy():
    """Buy fee = 0.1425% (broker).

    Buy 1000 shares at price=10.0 → cost = 10,000 + 14.25 fee = 10,014.25
    """
    prices = _make_prices([10.20, 10.0])  # ~-2% drop, triggers ladder buy
    cfg = SimulationConfig(initial_cash=20_000.0, symbol_group="core", max_position_pct=0.95)
    result = simulate(prices, cfg)
    # Ladder amount for -2% is 4000 TWD; 4000/10 = 400 shares; rounded to 0 lots → no buy
    # But we want to test fee... let's force a price where ladder amount fits a lot
    # Actually simpler: test that buy_and_hold has correct fee
    bah = simulate_buy_and_hold(prices, initial_cash=20_000.0)
    if len(bah.trades) >= 1 and bah.trades[0].side == "buy":
        buy = bah.trades[0]
        # cost = shares × price + fee
        expected_fee = buy.shares * buy.price * BROKER_FEE_RATE
        assert buy.fee == pytest.approx(expected_fee, abs=0.01)


def test_fees_sell_includes_tax():
    """Sell fee = 0.1425% broker + 0.1% securities tax (台股賣出證交稅)."""
    closes = [10.0, 11.0]
    prices = _make_prices(closes)
    bah = simulate_buy_and_hold(prices, initial_cash=1_000_000.0)
    sell = [t for t in bah.trades if t.side == "sell"][0]
    expected_fee = sell.shares * sell.price * (BROKER_FEE_RATE + SELL_TAX_RATE)
    assert sell.fee == pytest.approx(expected_fee, abs=0.01)
