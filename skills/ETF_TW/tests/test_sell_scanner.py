"""
Tests for auto_trade.sell_scanner
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts.auto_trade import sell_scanner as ss
from scripts.auto_trade import peak_tracker as pt

TW_TZ = ZoneInfo("Asia/Taipei")


@pytest.fixture
def state_dir(tmp_path):
    sd = tmp_path / "state"
    sd.mkdir()
    return sd


def _write(state_dir, name, payload):
    (state_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_intraday(symbol: str, latest_close: float):
    return {
        "intraday": {
            symbol: {
                "ticker_used": f"{symbol}.TW",
                "bars": [
                    {"t": "2026-04-25T09:00:00+08:00", "open": latest_close, "high": latest_close,
                     "low": latest_close, "close": latest_close, "volume": 1000}
                ],
                "bar_count": 1,
                "latest_close": latest_close,
                "latest_time": "2026-04-25T13:14:00+08:00",
            }
        }
    }


# ---------------------------------------------------------------------------
# 觸發 trailing stop（current_price < stop_price）
# ---------------------------------------------------------------------------

def test_run_sell_scan_triggers_when_below_stop(state_dir):
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("00923", 33.0))
    _write(state_dir, "market_cache.json", {"quotes": {}})

    # tracker：peak 35, trailing 5% → stop = 33.25；current 33.0 < 33.25 → 觸發
    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15",
            "tracking_start_date": "2026-04-16",
            "group": "income",
            "peak_close": 35.0,
            "peak_close_date": "2026-04-22",
            "trailing_pct": 0.05,
            "stop_price": 33.25,
            "is_locked_in": False,
            "last_updated": on_date.isoformat(),
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert len(res["enqueued"]) == 1
    sig = res["enqueued"][0]
    assert sig["symbol"] == "00923"
    assert sig["side"] == "sell"
    assert sig["order_type"] == "market"  # D7
    assert sig["quantity"] == 200
    assert "trailing stop" in sig["trigger_reason"]
    assert sig["trigger_payload"]["peak_close"] == 35.0
    assert sig["trigger_payload"]["stop_price"] == 33.25


def test_run_sell_scan_skips_trailing_during_active_initial_dca(state_dir):
    """初始 DCA 建倉期間應凍結 trailing sell，避免還在建倉就被洗出場。"""
    on_date = datetime(2026, 4, 29, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("00923", 33.0))
    _write(state_dir, "market_cache.json", {"quotes": {}})
    _write(state_dir, "initial_dca_state.json", {
        "enabled": True,
        "total_target_twd": 10000,
        "target_days": 10,
        "started_on": "2026-04-29",
        "days_done": 2,
        "twd_spent": 2000,
        "completed": False,
        "symbol_priority": ["00923"],
    })

    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15",
            "tracking_start_date": "2026-04-16",
            "group": "income",
            "peak_close": 35.0,
            "peak_close_date": "2026-04-22",
            "trailing_pct": 0.05,
            "stop_price": 33.25,
            "is_locked_in": False,
            "last_updated": on_date.isoformat(),
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)

    assert res["enqueued"] == []
    assert len(res["dca_trailing_frozen"]) == 1
    assert res["dca_trailing_frozen"][0]["symbol"] == "00923"


def test_run_sell_scan_above_stop_no_trigger(state_dir):
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("00923", 34.0))  # 34 >= 33.25
    _write(state_dir, "market_cache.json", {"quotes": {}})

    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15", "tracking_start_date": "2026-04-16",
            "group": "income", "peak_close": 35.0, "peak_close_date": "2026-04-22",
            "trailing_pct": 0.05, "stop_price": 33.25, "is_locked_in": False,
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert res["enqueued"] == []
    assert len(res["above_stop"]) == 1
    assert res["above_stop"][0]["symbol"] == "00923"


def test_run_sell_scan_tracking_not_started(state_dir):
    """D8=B：剛買進當天不該觸發賣出"""
    on_date = datetime(2026, 4, 15, 13, 15, tzinfo=TW_TZ)  # entry day

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("00923", 25.0))  # 暴跌
    _write(state_dir, "market_cache.json", {"quotes": {}})

    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15",
            "tracking_start_date": "2026-04-16",  # 還沒到
            "group": "income", "peak_close": 30.0, "peak_close_date": "2026-04-15",
            "trailing_pct": 0.05, "stop_price": 28.5, "is_locked_in": False,
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert res["enqueued"] == []
    assert len(res["tracking_not_started"]) == 1


def test_run_sell_scan_no_tracker_entry(state_dir):
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 100, "average_cost": 80, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("0050", 70.0))
    _write(state_dir, "market_cache.json", {"quotes": {}})
    # tracker 空，但持倉存在 → 應放到 tracking_not_started
    pt.save_tracker(state_dir, {})

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert res["enqueued"] == []
    assert len(res["tracking_not_started"]) == 1
    assert res["tracking_not_started"][0]["reason"] == "no_tracker_entry"


def test_run_sell_scan_no_intraday_falls_back_to_market_cache(state_dir):
    """無 intraday 但有 market_cache.current_price → 應仍能觸發"""
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    # intraday 無此 symbol
    _write(state_dir, "intraday_quotes_1m.json", {"intraday": {}})
    _write(state_dir, "market_cache.json", {
        "quotes": {"00923": {"current_price": 33.0}}  # 應 fallback 到這
    })
    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15", "tracking_start_date": "2026-04-16",
            "group": "income", "peak_close": 35.0, "peak_close_date": "2026-04-22",
            "trailing_pct": 0.05, "stop_price": 33.25, "is_locked_in": False,
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert len(res["enqueued"]) == 1


def test_run_sell_scan_inventory_check_passes(state_dir):
    """賣出數量 = 持倉數量 → gate 應通過（庫存檢查）"""
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "00923", "quantity": 1000, "average_cost": 30, "entry_date": "2026-04-15"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("00923", 33.0))
    _write(state_dir, "market_cache.json", {"quotes": {}})
    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-15", "tracking_start_date": "2026-04-16",
            "group": "income", "peak_close": 35.0, "peak_close_date": "2026-04-22",
            "trailing_pct": 0.05, "stop_price": 33.25, "is_locked_in": False,
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert len(res["enqueued"]) == 1
    assert res["enqueued"][0]["quantity"] == 1000
    assert res["enqueued"][0]["lot_type"] == "board"


def test_run_sell_scan_locked_in_signal_in_reason(state_dir):
    """鎖利狀態下觸發應在 trigger_reason 標示 locked-in"""
    on_date = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)

    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 100, "average_cost": 80, "entry_date": "2026-04-01"},
    ]})
    _write(state_dir, "intraday_quotes_1m.json", _make_intraday("0050", 96.0))  # 96 < 96.97
    _write(state_dir, "market_cache.json", {"quotes": {}})
    pt.save_tracker(state_dir, {
        "0050": {
            "entry_date": "2026-04-01", "tracking_start_date": "2026-04-02",
            "group": "core",
            "peak_close": 100.0, "peak_close_date": "2026-04-22",
            "trailing_pct": 0.03,  # 鎖利
            "stop_price": 97.0,
            "is_locked_in": True,
        }
    })

    res = ss.run_sell_scan(state_dir=state_dir, on_date=on_date)
    assert len(res["enqueued"]) == 1
    assert "locked-in" in res["enqueued"][0]["trigger_reason"]
    assert res["enqueued"][0]["trigger_payload"]["is_locked_in"] is True


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

def test_write_sell_cooldown(state_dir):
    sold_on = datetime(2026, 4, 25, 14, 0, tzinfo=TW_TZ)
    ss.write_sell_cooldown(state_dir, "00923", sold_on=sold_on)

    path = state_dir / "position_cooldown.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "00923" in data
    cooldown_until = datetime.fromisoformat(data["00923"]["cooldown_until"])
    expected = sold_on + timedelta(days=ss.SELL_COOLDOWN_DAYS)
    assert cooldown_until == expected


def test_write_sell_cooldown_overwrites_existing(state_dir):
    """第二次賣出同檔，cooldown 應更新"""
    sold_on_1 = datetime(2026, 4, 10, 14, 0, tzinfo=TW_TZ)
    sold_on_2 = datetime(2026, 4, 25, 14, 0, tzinfo=TW_TZ)
    ss.write_sell_cooldown(state_dir, "00923", sold_on=sold_on_1)
    ss.write_sell_cooldown(state_dir, "00923", sold_on=sold_on_2)
    data = json.loads((state_dir / "position_cooldown.json").read_text(encoding="utf-8"))
    assert data["00923"]["sold_at"] == sold_on_2.isoformat()
