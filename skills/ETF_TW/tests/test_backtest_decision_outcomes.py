"""
Unit tests for backtest_decision_outcomes.py
No real yfinance calls — all prices injected via price_fetcher param.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backtest_decision_outcomes import (
    compute_trade_pnl,
    compute_metrics,
    evaluate_quality_gate,
    run_backtest,
)


def make_price_fetcher(prices: dict):
    """prices = {(symbol, date_str): float}"""
    def fetch(symbol, date_str):
        return prices.get((symbol, date_str))
    return fetch


# --- PnL calculation tests ---

def test_buy_pnl_positive_on_price_rise():
    result = compute_trade_pnl(entry_price=100.0, exit_price=110.0, action="buy")
    assert abs(result - 0.10) < 1e-9


def test_sell_pnl_positive_on_price_fall():
    result = compute_trade_pnl(entry_price=100.0, exit_price=90.0, action="sell")
    assert abs(result - 0.10) < 1e-9


# --- compute_metrics tests ---

def test_metrics_win_rate_half():
    metrics = compute_metrics([0.1, -0.05, 0.08, -0.03])
    assert metrics["win_rate"] == 0.5


def test_metrics_all_wins():
    metrics = compute_metrics([0.1, 0.05, 0.08])
    assert metrics["win_rate"] == 1.0


def test_max_drawdown_calculation():
    # equity curve from pnl list [0.1, -0.2, 0.1]:
    # cumsum = [0.1, -0.1, 0.0]; equity = [1.1, 0.9, 1.0]
    # peak after first trade = 1.1; trough = 0.9 → drawdown = (1.1-0.9)/1.1 ≈ 0.1818
    metrics = compute_metrics([0.1, -0.2, 0.1])
    assert metrics["max_drawdown"] is not None
    assert metrics["max_drawdown"] > 0.0


# --- quality gate tests ---

def test_quality_gate_passes_when_thresholds_met():
    assert evaluate_quality_gate(win_rate=0.55, max_drawdown=0.10) is True


def test_quality_gate_fails_low_win_rate():
    assert evaluate_quality_gate(win_rate=0.45, max_drawdown=0.10) is False


def test_quality_gate_fails_high_drawdown():
    assert evaluate_quality_gate(win_rate=0.6, max_drawdown=0.20) is False


# --- empty input test ---

def test_empty_records_produces_null_metrics():
    result = run_backtest(records=[], price_fetcher=make_price_fetcher({}))
    assert result["quality_gate_passed"] is False
    assert result["win_rate"] is None
    assert result["max_drawdown"] is None
    assert result["total_decisions_evaluated"] == 0


# --- end-to-end mock test ---

def test_run_backtest_with_mock_prices():
    records = [
        {
            "request_id": "r1",
            "recorded_at": "2026-03-01T10:00:00+08:00",
            "symbol": "0050",
            "action": "preview_buy",
            "outcome_status": "tracked",
        },
        {
            "request_id": "r2",
            "recorded_at": "2026-03-01T10:00:00+08:00",
            "symbol": "0056",
            "action": "preview_sell",
            "outcome_status": "tracked",
        },
        {
            "request_id": "r3",
            "recorded_at": "2026-03-05T10:00:00+08:00",
            "symbol": "0050",
            "action": "hold",
            "outcome_status": "tracked",
        },
    ]

    prices = {
        # 0050 buy: entry 2026-03-01, exit 2026-03-06 (+5 cal days)
        ("0050", "2026-03-01"): 150.0,
        ("0050", "2026-03-06"): 165.0,  # +10%
        # 0056 sell: entry 2026-03-01, exit 2026-03-06
        ("0056", "2026-03-01"): 30.0,
        ("0056", "2026-03-06"): 27.0,   # -10% → sell profits
    }

    fetcher = make_price_fetcher(prices)
    result = run_backtest(records=records, holding_days=5, price_fetcher=fetcher)

    # hold actions should be filtered out — only 2 tradeable
    assert result["tradeable_decisions"] == 2
    assert result["trades_with_price_data"] == 2
    assert len(result["trade_details"]) == 2

    pnls = [t["pnl"] for t in result["trade_details"]]
    assert all(abs(p - 0.10) < 1e-6 for p in pnls)

    assert result["win_rate"] == 1.0
    assert result["quality_gate_passed"] is True
