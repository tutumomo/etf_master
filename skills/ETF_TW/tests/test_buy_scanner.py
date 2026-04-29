"""
Tests for auto_trade.buy_scanner
"""
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

pd = pytest.importorskip("pandas")

from scripts.auto_trade.buy_scanner import (
    DROP_LADDER,
    ladder_amount,
    run_buy_scan,
    _calc_lot_type_and_quantity,
)
from scripts.auto_trade.vwap_calculator import TW_TZ

# ---------------------------------------------------------------------------
# ladder_amount
# ---------------------------------------------------------------------------

def test_ladder_no_trigger_when_drop_below_1pct():
    assert ladder_amount(-0.5) == 0
    assert ladder_amount(0.0) == 0
    assert ladder_amount(0.5) == 0  # 漲也不買
    assert ladder_amount(-0.99) == 0


def test_ladder_1pct_drop():
    assert ladder_amount(-1.0) == 2000
    assert ladder_amount(-1.5) == 2000
    assert ladder_amount(-1.99) == 2000


def test_ladder_2pct_drop():
    assert ladder_amount(-2.0) == 4000
    assert ladder_amount(-2.5) == 4000
    assert ladder_amount(-2.99) == 4000


def test_ladder_3pct_drop():
    assert ladder_amount(-3.0) == 6000
    assert ladder_amount(-2.9999999999999916) == 6000
    assert ladder_amount(-3.5) == 6000


def test_ladder_4pct_drop():
    assert ladder_amount(-4.0) == 8000
    assert ladder_amount(-4.5) == 8000


def test_ladder_5pct_or_more():
    assert ladder_amount(-5.0) == 10000
    assert ladder_amount(-7.0) == 10000
    assert ladder_amount(-15.0) == 10000


# ---------------------------------------------------------------------------
# _calc_lot_type_and_quantity
# ---------------------------------------------------------------------------

def test_lot_type_zero_or_negative_price():
    assert _calc_lot_type_and_quantity(2000, 0) == ("odd", 0)
    assert _calc_lot_type_and_quantity(2000, -1) == ("odd", 0)


def test_lot_type_odd_lot():
    # 2000 / 100 = 20 股 → 不到 1000，零股
    lt, q = _calc_lot_type_and_quantity(2000, 100)
    assert lt == "odd"
    assert q == 20


def test_lot_type_board_lot():
    # 200000 / 100 = 2000 股 → 整 2 張
    lt, q = _calc_lot_type_and_quantity(200000, 100)
    assert lt == "board"
    assert q == 2000


def test_lot_type_partial_board_rounds_down():
    # 2500 股應被無條件捨去到 2000 股
    lt, q = _calc_lot_type_and_quantity(250000, 100)
    assert lt == "board"
    assert q == 2000


# ---------------------------------------------------------------------------
# run_buy_scan integration
# ---------------------------------------------------------------------------

def _make_intraday(symbol: str, start_time: datetime, prices: list[float], volume: int = 1000):
    """生成 fixture 用的 intraday bars"""
    bars = []
    for i, p in enumerate(prices):
        t = (start_time + timedelta(minutes=i)).isoformat()
        bars.append({
            "t": t,
            "open": p, "high": p + 0.1, "low": p - 0.1, "close": p,
            "volume": volume,
        })
    return bars


@pytest.fixture
def state_dir(tmp_path):
    """準備一個迷你 state 目錄"""
    sd = tmp_path / "state"
    sd.mkdir()
    return sd


def _write_state(state_dir: Path, name: str, payload: dict):
    (state_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_run_buy_scan_no_data(state_dir):
    """完全空的 state → 無任何訊號"""
    _write_state(state_dir, "watchlist.json", {"items": []})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {"intraday": {}})
    _write_state(state_dir, "market_cache.json", {"quotes": {}})
    _write_state(state_dir, "account_snapshot.json", {"cash": 10000, "settlement_safe_cash": 10000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })

    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )
    assert res["enqueued"] == []
    assert res["candidates"] == 0


def test_run_buy_scan_drop_2pct_triggers_buy(state_dir):
    """單一檔跌 2.5% 應觸發 4000 TWD 買入訊號"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    # 昨收 100 元，盤中 09:00–09:30 平均 97.5 元 → 跌 2.5% → 4000 TWD
    intraday = {
        "intraday": {
            "0050": {
                "ticker_used": "0050.TW",
                "bars": _make_intraday("0050", bar_start, [97.5] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 97.5,
                "latest_time": bar_start.isoformat(),
            }
        }
    }

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", intraday)
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0050": {"current_price": 97.5, "prev_close": 100.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {
        "cash": 100000, "settlement_safe_cash": 100000,
    })
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )
    assert res["skipped"] is None
    assert len(res["enqueued"]) == 1, f"Expected 1 enqueued, got: {res}"
    sig = res["enqueued"][0]
    assert sig["symbol"] == "0050"
    assert sig["side"] == "buy"
    # v2: 1% × 100k = 1000 TWD / 97.5 ≈ 10 股（零股）
    assert sig["quantity"] == 10
    assert sig["lot_type"] == "odd"
    assert "VWAP 跌" in sig["trigger_reason"]
    assert sig["trigger_source"] == "buy_scanner_0930"
    # payload 帶 vwap / drop_pct / ladder_amount
    assert sig["trigger_payload"]["ladder_amount"] == 1000  # v2: 1% × 100k cash
    assert sig["trigger_payload"]["drop_pct"] == pytest.approx(-2.5, abs=0.5)


def test_run_buy_scan_enqueues_initial_dca_signal_without_intraday_bars(state_dir):
    """DCA 啟用時，即使沒有 VWAP intraday bars，也應依 current_price 建立待確認買單。"""
    on_date = datetime(2026, 4, 29, 9, 30, tzinfo=TW_TZ)

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {"intraday": {}})
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0050": {"current_price": 50.0, "prev_close": 51.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True,
        "max_buy_amount_pct": 0.5,
        "max_buy_amount_twd": 1000000,
        "max_buy_shares": 1000,
    })
    _write_state(state_dir, "initial_dca_state.json", {
        "enabled": True,
        "total_target_twd": 10000,
        "target_days": 10,
        "started_on": "2026-04-29",
        "days_done": 0,
        "twd_spent": 0,
        "completed": False,
        "last_buy_date": None,
        "symbol_priority": ["0050"],
        "next_symbol_idx": 0,
    })

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert len(res["enqueued"]) == 1
    sig = res["enqueued"][0]
    assert sig["symbol"] == "0050"
    assert sig["quantity"] == 20
    assert sig["trigger_source"] == "initial_dca"
    assert sig["trigger_payload"]["initial_dca"] is True
    assert sig["trigger_payload"]["amount_twd"] == 1000
    assert sig["trigger_payload"]["next_symbol_idx"] == 0


def test_run_buy_scan_does_not_duplicate_pending_dca_same_day(state_dir):
    """同一天已有 DCA pending 時，不應在下一個掃描時點重複 enqueue。"""
    on_date = datetime(2026, 4, 29, 11, 0, tzinfo=TW_TZ)
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {"intraday": {}})
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0050": {"current_price": 50.0, "prev_close": 51.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True,
        "max_buy_amount_pct": 0.5,
        "max_buy_amount_twd": 1000000,
        "max_buy_shares": 1000,
    })
    _write_state(state_dir, "initial_dca_state.json", {
        "enabled": True,
        "total_target_twd": 10000,
        "target_days": 10,
        "started_on": "2026-04-29",
        "days_done": 0,
        "twd_spent": 0,
        "completed": False,
        "last_buy_date": None,
        "symbol_priority": ["0050"],
        "next_symbol_idx": 0,
    })
    _write_state(state_dir, "pending_auto_orders.json", [{
        "id": "existing-dca",
        "side": "buy",
        "symbol": "0050",
        "quantity": 20,
        "price": 50.0,
        "order_type": "limit",
        "lot_type": "odd",
        "trigger_source": "initial_dca",
        "trigger_payload": {"initial_dca": True},
        "created_at": "2026-04-29T09:30:00+08:00",
        "expires_at": "2026-04-29T09:45:00+08:00",
        "status": "pending",
    }])

    res = run_buy_scan(
        trigger_time=time(11, 0),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert res["enqueued"] == []
    assert res["dca"]["skipped"] == "already_pending_or_done_today"


def test_run_buy_scan_below_threshold_no_signal(state_dir):
    """跌幅 < 1% → 不觸發"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    # 昨收 100，VWAP 99.5 → 跌 0.5%
    intraday = {
        "intraday": {
            "0056": {
                "ticker_used": "0056.TW",
                "bars": _make_intraday("0056", bar_start, [99.5] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 99.5,
                "latest_time": bar_start.isoformat(),
            }
        }
    }
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0056"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", intraday)
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0056": {"current_price": 99.5, "prev_close": 100.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })

    res = run_buy_scan(
        trigger_time=time(9, 30), state_dir=state_dir,
        on_date=on_date, skip_circuit_breaker=True,
    )
    assert res["enqueued"] == []
    assert len(res["below_threshold"]) == 1
    assert res["below_threshold"][0]["symbol"] == "0056"


def test_run_buy_scan_skips_symbol_during_post_sell_cooldown(state_dir):
    """賣出 cooldown 期間，即使 VWAP 跌幅達標也不應重新入 queue。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    intraday = {
        "intraday": {
            "00923": {
                "ticker_used": "00923.TW",
                "bars": _make_intraday("00923", bar_start, [33.0] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 33.0,
                "latest_time": bar_start.isoformat(),
            }
        }
    }
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "00923"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", intraday)
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"00923": {"current_price": 33.0, "prev_close": 35.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })
    _write_state(state_dir, "position_cooldown.json", {
        "00923": {
            "sold_at": "2026-04-24T13:30:00+08:00",
            "cooldown_until": "2026-05-01T13:30:00+08:00",
        }
    })

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert res["enqueued"] == []
    assert res["blocked"] == []
    assert res["below_threshold"] == []
    assert len(res["cooldown"]) == 1
    assert res["cooldown"][0]["symbol"] == "00923"
    assert res["cooldown"][0]["reason"] == "post_sell_cooldown"


def test_run_buy_scan_applies_strategy_and_overlay_amount_adjustment(state_dir):
    """Phase 2 買入會把原始階梯金額依策略與 overlay 調整後再入 queue。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "00878", "group": "income"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {
        "intraday": {
            "00878": {
                "ticker_used": "00878.TW",
                "bars": _make_intraday("00878", bar_start, [19.5] * 30, volume=1000),
                "bar_count": 30,
            }
        }
    })
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"00878": {"current_price": 20.0, "prev_close": 20.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })
    _write_state(state_dir, "strategy_link.json", {"base_strategy": "收益優先", "scenario_overlay": "收益再投資"})
    _write_state(state_dir, "market_context_taiwan.json", {"risk_temperature": "normal", "market_regime": "normal"})

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert len(res["enqueued"]) == 1
    sig = res["enqueued"][0]
    # v2: base=1% × 100k = 1000，overlay 1.25 → 1250，price=20 → 62 股
    assert sig["quantity"] == 62
    assert sig["trigger_payload"]["base_ladder_amount"] == 1000
    assert sig["trigger_payload"]["ladder_amount"] == 1250
    assert sig["trigger_payload"]["base_strategy"] == "收益優先"
    assert sig["trigger_payload"]["scenario_overlay"] == "收益再投資"
    assert sig["trigger_payload"]["group"] == "income"
    assert sig["trigger_payload"]["overlay_multiplier"] == 1.25


def test_run_buy_scan_macro_cautious_blocks_all_buy_signals(state_dir):
    """macro_cautious 應是明確買入 gate：不產生任何 buy pending。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050", "group": "core"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {
        "intraday": {
            "0050": {
                "ticker_used": "0050.TW",
                "bars": _make_intraday("0050", bar_start, [97.5] * 30, volume=1000),
                "bar_count": 30,
            }
        }
    })
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0050": {"current_price": 97.5, "prev_close": 100.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })
    _write_state(state_dir, "market_context_taiwan.json", {
        "macro_signals": {"macro_label": "macro_cautious", "macro_score": -2}
    })

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert res["enqueued"] == []
    assert res["skipped"] == "macro_regime_gate"
    assert res["macro_gate"]["action"] == "block_buy"


def test_run_buy_scan_macro_neutral_halves_ladder_amount(state_dir):
    """macro_neutral 應把買入 sizing 減半，但仍允許進入紅線檢查。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050", "group": "core"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {
        "intraday": {
            "0050": {
                "ticker_used": "0050.TW",
                "bars": _make_intraday("0050", bar_start, [97.5] * 30, volume=1000),
                "bar_count": 30,
            }
        }
    })
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"0050": {"current_price": 50.0, "prev_close": 100.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
    })
    _write_state(state_dir, "market_context_taiwan.json", {
        "macro_signals": {"macro_label": "macro_neutral", "macro_score": 0}
    })

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert len(res["enqueued"]) == 1
    sig = res["enqueued"][0]
    assert sig["trigger_payload"]["base_ladder_amount"] == 1000
    assert sig["trigger_payload"]["ladder_amount"] == 500
    assert sig["trigger_payload"]["macro_multiplier"] == 0.5


def test_run_buy_scan_skips_growth_in_cautious_market_until_deeper_drop(state_dir):
    """謹慎/高風險情境下，growth 類跌幅未達加嚴門檻時不入 queue。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "00830", "group": "growth"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {
        "intraday": {
            "00830": {
                "ticker_used": "00830.TW",
                "bars": _make_intraday("00830", bar_start, [97.5] * 30, volume=1000),
                "bar_count": 30,
            }
        }
    })
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"00830": {"current_price": 97.5, "prev_close": 100.0}}
    })
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {"enabled": True, "max_buy_amount_pct": 0.5})
    _write_state(state_dir, "strategy_link.json", {"base_strategy": "平衡配置", "scenario_overlay": "無"})
    _write_state(state_dir, "market_context_taiwan.json", {"risk_temperature": "elevated", "market_regime": "cautious"})

    res = run_buy_scan(
        trigger_time=time(9, 30),
        state_dir=state_dir,
        on_date=on_date,
        skip_circuit_breaker=True,
    )

    assert res["enqueued"] == []
    assert len(res["strategy_skipped"]) == 1
    assert res["strategy_skipped"][0]["symbol"] == "00830"
    assert res["strategy_skipped"][0]["reason"] == "cautious_growth_threshold"


def test_run_buy_scan_gate_blocked_writes_history(state_dir):
    """sizing limit 擋下 → 不入 queue，寫 history (gate_blocked)"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    # v2: 跌 5% → 階梯 2.5% × 100k = 2500 TWD；max_conc=0.01 → 上限 1000 < 2500 必擋
    intraday = {
        "intraday": {
            "00923": {
                "ticker_used": "00923.TW",
                "bars": _make_intraday("00923", bar_start, [33.0] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 33.0,
                "latest_time": bar_start.isoformat(),
            }
        }
    }
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "00923"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", intraday)
    _write_state(state_dir, "market_cache.json", {
        "quotes": {"00923": {"current_price": 33.0, "prev_close": 35.0}}
    })
    # ssc=100k → ladder=2500；max_conc=0.01 → 上限 1000 < 2500 必擋
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 100000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.01, "max_buy_amount_twd": 1000000,
    })

    res = run_buy_scan(
        trigger_time=time(9, 30), state_dir=state_dir,
        on_date=on_date, skip_circuit_breaker=True,
    )
    assert res["enqueued"] == []
    assert len(res["blocked"]) == 1
    assert res["blocked"][0]["symbol"] == "00923"
    assert res["blocked"][0]["reason"] == "exceeds_sizing_limit"
    # history 應該有一筆 gate_blocked
    history_path = state_dir / "auto_trade_history.jsonl"
    assert history_path.exists()
    lines = history_path.read_text(encoding="utf-8").strip().split("\n")
    rec = json.loads(lines[0])
    assert rec["_event"] == "gate_blocked"


def test_run_buy_scan_blocks_second_candidate_when_daily_amount_would_exceed_safe_cash(state_dir):
    """同一輪掃描多檔候選時，pending + 本筆不能超過可交割金額比例。"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    intraday = {
        "intraday": {
            "0050": {
                "ticker_used": "0050.TW",
                "bars": _make_intraday("0050", bar_start, [33.0] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 33.0,
                "latest_time": bar_start.isoformat(),
            },
            "00923": {
                "ticker_used": "00923.TW",
                "bars": _make_intraday("00923", bar_start, [33.0] * 30, volume=1000),
                "bar_count": 30,
                "latest_close": 33.0,
                "latest_time": bar_start.isoformat(),
            },
        }
    }
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050"}, {"symbol": "00923"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", intraday)
    _write_state(state_dir, "market_cache.json", {
        "quotes": {
            "0050": {"current_price": 33.0, "prev_close": 35.0},
            "00923": {"current_price": 33.0, "prev_close": 35.0},
        }
    })
    # v2: ladder 跌-5.7% → 2.5% × 30k = 750 TWD/檔
    # 設 max_buy_amount_pct=0.04 → 上限 1200，兩檔 1500 > 1200 必擋第二
    _write_state(state_dir, "account_snapshot.json", {"cash": 100000, "settlement_safe_cash": 30000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": True,
        "max_buy_amount_pct": 0.04,
        "max_buy_amount_twd": 1000000,
        "max_buy_shares": 1000,
        "daily_max_buy_submits": 10,
    })

    res = run_buy_scan(
        trigger_time=time(9, 30), state_dir=state_dir,
        on_date=on_date, skip_circuit_breaker=True,
    )

    assert len(res["enqueued"]) == 1
    assert len(res["blocked"]) == 1
    assert res["blocked"][0]["reason"] == "daily_buy_amount_limit"
    assert res["blocked"][0]["details"]["limit"] == 1200  # v2: 30k × 0.04
    assert res["blocked"][0]["details"]["used_today"] > 0


def test_run_buy_scan_circuit_breaker_skips_all(state_dir):
    """master switch off → 整體跳過"""
    _write_state(state_dir, "watchlist.json", {"items": [{"symbol": "0050"}]})
    _write_state(state_dir, "positions.json", {"positions": []})
    _write_state(state_dir, "intraday_quotes_1m.json", {"intraday": {}})
    _write_state(state_dir, "market_cache.json", {"quotes": {}})
    _write_state(state_dir, "account_snapshot.json", {"cash": 10000, "settlement_safe_cash": 10000})
    _write_state(state_dir, "safety_redlines.json", {})
    # auto_trade_config 不存在 → 預設 enabled=False
    _write_state(state_dir, "market_event_context.json", {"event_regime": "neutral", "global_risk_level": "low"})
    _write_state(state_dir, "major_event_flag.json", {"triggered": False})

    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    res = run_buy_scan(
        trigger_time=time(9, 30), state_dir=state_dir,
        on_date=on_date, skip_circuit_breaker=False,
    )
    assert res["skipped"] == "circuit_breaker"
    # 確認 reasons 列表不為空
    assert "master_switch" in str(res.get("circuit_breaker_reasons", []))
