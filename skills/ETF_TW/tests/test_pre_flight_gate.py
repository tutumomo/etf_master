"""
Tests for pre_flight_gate:
  - _pass() returns empty reason string (T1 fix)
  - compute_investment_score() factor logic (T2)
  - check_order() appends investment_score on pass
"""
import pytest
from scripts.pre_flight_gate import _pass, _fail, compute_investment_score, check_order


# ---------------------------------------------------------------------------
# T1: _pass() reason is empty string, not 'passed'
# ---------------------------------------------------------------------------

def test_pass_reason_is_empty_string():
    result = _pass()
    assert result["passed"] is True
    assert result["reason"] == ""


def test_fail_reason_is_non_empty():
    result = _fail("missing_symbol")
    assert result["passed"] is False
    assert result["reason"] == "missing_symbol"


# ---------------------------------------------------------------------------
# T2: compute_investment_score factor logic
# ---------------------------------------------------------------------------

def _base_order(**kwargs):
    o = {"symbol": "0050", "side": "buy", "quantity": 100, "price": 100.0}
    o.update(kwargs)
    return o


def _base_ctx(**kwargs):
    c = {"cash": 10000.0, "_skip_safety_redlines": True}
    c.update(kwargs)
    return c


def test_score_ai_confidence_high():
    # Use large cash so sizing ratio < 15% (adds +2), no regime, no alignment
    # high +3, small order +2 = +5 minimum (trading hours ±1 varies)
    result = compute_investment_score(
        _base_order(ai_confidence="high", quantity=100, price=10.0),
        _base_ctx(cash=100_000.0)
    )
    assert result["investment_score"] >= 5
    assert any("high" in b for b in result["score_breakdown"])


def test_score_ai_confidence_medium():
    # Use large cash so sizing adds +2, medium +1 → at least +3 (trading hours ±1 varies)
    result = compute_investment_score(
        _base_order(ai_confidence="medium", quantity=100, price=10.0),
        _base_ctx(cash=100_000.0)
    )
    assert result["investment_score"] >= 3
    assert any("medium" in b for b in result["score_breakdown"])


def test_score_ai_confidence_low():
    result = compute_investment_score(_base_order(ai_confidence="low"), _base_ctx())
    assert result["investment_score"] <= -1
    assert any("low" in b for b in result["score_breakdown"])


def test_score_strategy_aligned_adds_two():
    without = compute_investment_score(_base_order(), _base_ctx(strategy_aligned=False))
    with_aligned = compute_investment_score(_base_order(), _base_ctx(strategy_aligned=True))
    assert with_aligned["investment_score"] == without["investment_score"] + 2
    assert any("策略對齊" in b for b in with_aligned["score_breakdown"])


def test_score_small_order_adds_two():
    # quantity=100, price=10 → order_amount=1000, cash=100000 → ratio=1% < 15%
    result = compute_investment_score(
        _base_order(quantity=100, price=10.0),
        _base_ctx(cash=100_000.0)
    )
    assert any("規模合理" in b for b in result["score_breakdown"])


def test_score_large_order_subtracts_two():
    # quantity=1000, price=100 → order_amount=100_000, cash=200_000 → ratio=50% > 25%
    result = compute_investment_score(
        _base_order(quantity=1000, price=100.0),
        _base_ctx(cash=200_000.0)
    )
    assert any("規模偏高" in b for b in result["score_breakdown"])


def test_score_market_cautious_subtracts_two():
    result = compute_investment_score(_base_order(), _base_ctx(market_regime="cautious"))
    assert any("cautious" in b for b in result["score_breakdown"])


def test_score_market_bullish_adds_one():
    result = compute_investment_score(_base_order(), _base_ctx(market_regime="bullish"))
    assert any("bullish" in b for b in result["score_breakdown"])


def test_score_clamped_to_minus_ten():
    # low confidence + cautious + large order = -2 -2 -2 = -6, well within range
    result = compute_investment_score(
        _base_order(ai_confidence="low", quantity=1000, price=100.0),
        _base_ctx(market_regime="cautious", cash=200_000.0)
    )
    assert result["investment_score"] >= -10


def test_score_clamped_to_plus_ten():
    result = compute_investment_score(
        _base_order(ai_confidence="high"),
        _base_ctx(strategy_aligned=True, market_regime="bullish")
    )
    assert result["investment_score"] <= 10


# ---------------------------------------------------------------------------
# T2: check_order() appends investment_score on pass
# ---------------------------------------------------------------------------

def test_check_order_pass_includes_investment_score():
    order = {
        "symbol": "0050",
        "side": "buy",
        "quantity": 100,
        "price": 100.0,
        "order_type": "limit",
        "lot_type": "odd",
    }
    ctx = {
        "cash": 100_000.0,
        "force_trading_hours": False,
        "_skip_safety_redlines": True,
        "market_regime": "normal",
    }
    result = check_order(order, ctx)
    assert result["passed"] is True
    assert result["reason"] == ""
    assert "investment_score" in result
    assert isinstance(result["investment_score"], int)
    assert "score_breakdown" in result
    assert isinstance(result["score_breakdown"], list)


def test_check_order_blocks_buy_when_portfolio_risk_report_blocks():
    order = {
        "symbol": "0050",
        "side": "buy",
        "quantity": 100,
        "price": 100.0,
        "order_type": "limit",
        "lot_type": "odd",
    }
    ctx = {
        "cash": 100_000.0,
        "force_trading_hours": False,
        "_skip_safety_redlines": True,
        "portfolio_risk_report": {
            "block_buy": True,
            "blockers": ["max_drawdown_block"],
            "portfolio": {"max_drawdown": 0.22},
        },
    }
    result = check_order(order, ctx)
    assert result["passed"] is False
    assert result["reason"] == "portfolio_risk_block_buy"
    assert result["details"]["blockers"] == ["max_drawdown_block"]


def test_check_order_fail_has_no_investment_score():
    order = {
        "symbol": "",   # triggers missing_symbol
        "side": "buy",
        "quantity": 100,
        "price": 100.0,
        "order_type": "limit",
        "lot_type": "odd",
    }
    ctx = {"cash": 100_000.0, "force_trading_hours": False, "_skip_safety_redlines": True}
    result = check_order(order, ctx)
    assert result["passed"] is False
    assert result["reason"] == "missing_symbol"
    # Failed fast — no investment_score key
    assert "investment_score" not in result
