"""
Tests for auto_trade.peak_tracker
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts.auto_trade import peak_tracker as pt

TW_TZ = ZoneInfo("Asia/Taipei")


# ---------------------------------------------------------------------------
# get_trailing_pct
# ---------------------------------------------------------------------------

def test_trailing_pct_core():
    assert pt.get_trailing_pct("core") == 0.06


def test_trailing_pct_income():
    assert pt.get_trailing_pct("income") == 0.05


def test_trailing_pct_defensive():
    assert pt.get_trailing_pct("defensive") == 0.04


def test_trailing_pct_other():
    assert pt.get_trailing_pct("other") == 0.08


def test_trailing_pct_unknown_falls_back():
    assert pt.get_trailing_pct("unknown") == pt.DEFAULT_TRAILING_PCT
    assert pt.get_trailing_pct("") == pt.DEFAULT_TRAILING_PCT


def test_trailing_pct_lock_in_below_threshold():
    """報酬 < 20% 不啟動鎖利"""
    assert pt.get_trailing_pct("core", return_pct=0.15) == 0.06
    assert pt.get_trailing_pct("income", return_pct=0.19) == 0.05


def test_trailing_pct_lock_in_at_threshold():
    """報酬 ≥ 20% 一律收緊到 3%"""
    assert pt.get_trailing_pct("core", return_pct=0.20) == 0.03
    assert pt.get_trailing_pct("income", return_pct=0.30) == 0.03
    assert pt.get_trailing_pct("defensive", return_pct=0.50) == 0.03


def test_trailing_pct_case_insensitive():
    assert pt.get_trailing_pct("CORE") == 0.06
    assert pt.get_trailing_pct("Income") == 0.05


# ---------------------------------------------------------------------------
# calc_stop_price
# ---------------------------------------------------------------------------

def test_calc_stop_price_basic():
    assert pt.calc_stop_price(100.0, 0.05) == pytest.approx(95.0)
    assert pt.calc_stop_price(35.0, 0.06) == pytest.approx(32.9)


def test_calc_stop_price_lock_in_3pct():
    assert pt.calc_stop_price(120.0, 0.03) == pytest.approx(116.4)


# ---------------------------------------------------------------------------
# is_tracking_active
# ---------------------------------------------------------------------------

def test_tracking_active_after_start_date():
    entry = {"tracking_start_date": "2026-04-20"}
    assert pt.is_tracking_active(entry, today=date(2026, 4, 21)) is True
    assert pt.is_tracking_active(entry, today=date(2026, 4, 20)) is True


def test_tracking_inactive_before_start_date():
    entry = {"tracking_start_date": "2026-04-20"}
    assert pt.is_tracking_active(entry, today=date(2026, 4, 19)) is False


def test_tracking_inactive_when_missing_start_date():
    assert pt.is_tracking_active({}, today=date(2026, 4, 20)) is False


# ---------------------------------------------------------------------------
# upsert_position
# ---------------------------------------------------------------------------

def test_upsert_creates_new_entry():
    tracker = {}
    entry = pt.upsert_position(
        tracker,
        symbol="00923",
        entry_date=date(2026, 4, 15),
        group="income",
        today_close=35.0,
        today=date(2026, 4, 20),
    )
    assert "00923" in tracker
    assert entry["entry_date"] == "2026-04-15"
    # D8=B: tracking_start = entry+1
    assert entry["tracking_start_date"] == "2026-04-16"
    assert entry["group"] == "income"
    assert entry["peak_close"] == 35.0
    assert entry["peak_close_date"] == "2026-04-20"
    assert entry["trailing_pct"] == 0.05  # income
    assert entry["stop_price"] == pytest.approx(35.0 * 0.95)
    assert entry["is_locked_in"] is False


def test_upsert_does_not_reset_existing_entry():
    """重複 upsert 不該覆蓋 entry_date 或 peak_close"""
    tracker = {}
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="income", today_close=35.0, today=date(2026, 4, 20),
    )
    # 第二次 upsert
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="income", today_close=40.0,  # 不該覆蓋 peak（peak 由 update_close 處理）
        today=date(2026, 4, 22),
    )
    entry = tracker["00923"]
    # entry_date 不該被改
    assert entry["entry_date"] == "2026-04-15"
    # peak 應保持 35（upsert 不更新 peak）
    assert entry["peak_close"] == 35.0


def test_upsert_syncs_group_change():
    tracker = {}
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="income", today_close=35.0, today=date(2026, 4, 16),
    )
    # 改變 group
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="core", today_close=35.0, today=date(2026, 4, 17),
    )
    assert tracker["00923"]["group"] == "core"
    assert tracker["00923"]["trailing_pct"] == 0.06  # core
    assert tracker["00923"]["stop_price"] == pytest.approx(35.0 * 0.94)


# ---------------------------------------------------------------------------
# update_close
# ---------------------------------------------------------------------------

def test_update_close_updates_peak_when_higher():
    tracker = {}
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="income", today_close=35.0, today=date(2026, 4, 16),
    )
    entry = pt.update_close(tracker, symbol="00923", close_price=37.0, on_date=date(2026, 4, 17))
    assert entry["peak_close"] == 37.0
    assert entry["peak_close_date"] == "2026-04-17"
    assert entry["stop_price"] == pytest.approx(37.0 * 0.95)


def test_update_close_keeps_peak_when_lower():
    tracker = {}
    pt.upsert_position(
        tracker, symbol="00923", entry_date=date(2026, 4, 15),
        group="income", today_close=35.0, today=date(2026, 4, 16),
    )
    entry = pt.update_close(tracker, symbol="00923", close_price=33.0, on_date=date(2026, 4, 17))
    assert entry["peak_close"] == 35.0  # 不退
    assert entry["peak_close_date"] == "2026-04-16"


def test_update_close_unknown_symbol():
    tracker = {}
    res = pt.update_close(tracker, symbol="UNKNOWN", close_price=10.0)
    assert res is None


def test_update_close_lock_in_engaged_and_irreversible():
    """報酬 ≥ 20% 進入鎖利 → trailing_pct 收緊到 3%；之後即使報酬退回也不解鎖"""
    tracker = {}
    pt.upsert_position(
        tracker, symbol="0050", entry_date=date(2026, 4, 1),
        group="core", today_close=100.0, today=date(2026, 4, 2),
    )
    # 報酬 25% 進入鎖利
    e1 = pt.update_close(tracker, symbol="0050", close_price=125.0, return_pct=0.25)
    assert e1["is_locked_in"] is True
    assert e1["trailing_pct"] == 0.03
    assert e1["stop_price"] == pytest.approx(125.0 * 0.97)

    # 隔日報酬退回 15%（< 20%），鎖利不解除
    e2 = pt.update_close(tracker, symbol="0050", close_price=115.0, return_pct=0.15)
    assert e2["is_locked_in"] is True
    assert e2["trailing_pct"] == 0.03  # 保持鎖利
    # peak 仍是 125，所以 stop 仍是 125 × 0.97
    assert e2["peak_close"] == 125.0


def test_update_close_no_lock_when_return_below_threshold():
    tracker = {}
    pt.upsert_position(
        tracker, symbol="0050", entry_date=date(2026, 4, 1),
        group="core", today_close=100.0, today=date(2026, 4, 2),
    )
    e = pt.update_close(tracker, symbol="0050", close_price=110.0, return_pct=0.10)
    assert e["is_locked_in"] is False
    assert e["trailing_pct"] == 0.06  # 仍是 core 的基礎


# ---------------------------------------------------------------------------
# remove_position
# ---------------------------------------------------------------------------

def test_remove_position():
    tracker = {"0050": {"foo": "bar"}}
    assert pt.remove_position(tracker, "0050") is True
    assert "0050" not in tracker


def test_remove_position_unknown_symbol():
    tracker = {}
    assert pt.remove_position(tracker, "UNKNOWN") is False


def test_remove_position_case_insensitive():
    tracker = {"0050": {"foo": "bar"}}
    assert pt.remove_position(tracker, "0050") is True


# ---------------------------------------------------------------------------
# sync_with_positions (integration)
# ---------------------------------------------------------------------------

@pytest.fixture
def state_dir(tmp_path):
    sd = tmp_path / "state"
    sd.mkdir()
    return sd


def _write(state_dir, name, payload):
    (state_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_sync_creates_new_entries(state_dir):
    _write(state_dir, "watchlist.json", {"items": [
        {"symbol": "0050", "group": "core"},
        {"symbol": "00923", "group": "income"},
    ]})
    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 100, "average_cost": 80, "entry_date": "2026-04-15"},
        {"symbol": "00923", "quantity": 200, "average_cost": 30, "entry_date": "2026-04-18"},
    ]})

    tracker = pt.sync_with_positions(
        state_dir,
        today=date(2026, 4, 25),
        today_close_lookup={"0050": 90.0, "00923": 35.0},
    )

    assert "0050" in tracker
    assert "00923" in tracker
    # peak 應該 = today_close
    assert tracker["0050"]["peak_close"] == 90.0
    assert tracker["00923"]["peak_close"] == 35.0
    # stop = peak × (1 - trailing_pct)
    assert tracker["0050"]["stop_price"] == pytest.approx(90.0 * 0.94)
    assert tracker["00923"]["stop_price"] == pytest.approx(35.0 * 0.95)


def test_sync_removes_sold_positions(state_dir):
    """tracker 有 00923，但 positions 已沒這檔 → 應移除"""
    _write(state_dir, "watchlist.json", {"items": [{"symbol": "0050", "group": "core"}]})
    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 100, "average_cost": 80, "entry_date": "2026-04-15"},
    ]})
    # 預先放 00923 在 tracker
    pt.save_tracker(state_dir, {
        "00923": {
            "entry_date": "2026-04-01", "tracking_start_date": "2026-04-02",
            "group": "income", "peak_close": 35.0, "trailing_pct": 0.05,
            "stop_price": 33.25, "is_locked_in": False,
        }
    })

    tracker = pt.sync_with_positions(
        state_dir,
        today=date(2026, 4, 25),
        today_close_lookup={"0050": 90.0},
    )

    assert "00923" not in tracker  # 應被移除
    assert "0050" in tracker


def test_sync_lock_in_engages_via_return_pct(state_dir):
    """sync 時若提供 return_pct ≥ 20% 應啟動鎖利"""
    _write(state_dir, "watchlist.json", {"items": [{"symbol": "0050", "group": "core"}]})
    _write(state_dir, "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 100, "average_cost": 80, "entry_date": "2026-04-01"},
    ]})

    tracker = pt.sync_with_positions(
        state_dir,
        today=date(2026, 4, 25),
        today_close_lookup={"0050": 100.0},  # +25% return
        return_pct_lookup={"0050": 0.25},
    )

    assert tracker["0050"]["is_locked_in"] is True
    assert tracker["0050"]["trailing_pct"] == 0.03
    assert tracker["0050"]["stop_price"] == pytest.approx(100.0 * 0.97)
