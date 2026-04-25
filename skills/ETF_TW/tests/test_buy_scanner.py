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
    # 4000 / 97.5 ≈ 41 股（零股）
    assert sig["quantity"] == 41
    assert sig["lot_type"] == "odd"
    assert "VWAP 跌" in sig["trigger_reason"]
    assert sig["trigger_source"] == "buy_scanner_0930"
    # payload 帶 vwap / drop_pct / ladder_amount
    assert sig["trigger_payload"]["ladder_amount"] == 4000
    assert sig["trigger_payload"]["drop_pct"] == pytest.approx(-2.5, abs=0.5)


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


def test_run_buy_scan_gate_blocked_writes_history(state_dir):
    """sizing limit 擋下 → 不入 queue，寫 history (gate_blocked)"""
    on_date = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    bar_start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)

    # 跌 5% → 階梯 10000；但 settlement_safe_cash 只有 1000，max_conc=0.5 → 上限 500 < 10000
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
    # 可交割只有 1000，買 10000 必擋
    _write_state(state_dir, "account_snapshot.json", {"cash": 5000, "settlement_safe_cash": 1000})
    _write_state(state_dir, "safety_redlines.json", {
        "enabled": False, "max_buy_amount_pct": 0.5, "max_buy_amount_twd": 1000000,
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
