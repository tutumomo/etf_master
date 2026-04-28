"""
Tests for auto_trade.initial_dca:
  - default_state / load / save
  - is_dca_phase_active
  - dca_should_trigger 各種情境
  - record_dca_buy 計入狀態
  - start_dca / stop_dca
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.auto_trade.initial_dca import (
    default_state,
    load_dca_state,
    save_dca_state,
    is_dca_phase_active,
    dca_should_trigger,
    record_dca_buy,
    start_dca,
    stop_dca,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def state_dir(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# default / load / save
# ---------------------------------------------------------------------------

def test_default_state_disabled():
    s = default_state()
    assert s["enabled"] is False
    assert s["completed"] is False
    assert s["days_done"] == 0
    assert s["twd_spent"] == 0


def test_load_returns_default_when_missing(state_dir):
    s = load_dca_state(state_dir)
    assert s == default_state()


def test_save_then_load_roundtrip(state_dir):
    s = default_state()
    s["enabled"] = True
    s["total_target_twd"] = 500_000
    save_dca_state(state_dir, s)
    s2 = load_dca_state(state_dir)
    assert s2["enabled"] is True
    assert s2["total_target_twd"] == 500_000


# ---------------------------------------------------------------------------
# is_dca_phase_active
# ---------------------------------------------------------------------------

def test_phase_inactive_when_disabled():
    s = default_state()
    s["enabled"] = False
    assert is_dca_phase_active(s) is False


def test_phase_inactive_when_completed():
    s = default_state()
    s["enabled"] = True
    s["completed"] = True
    assert is_dca_phase_active(s) is False


def test_phase_active_when_in_progress():
    s = default_state()
    s["enabled"] = True
    s["target_days"] = 20
    s["days_done"] = 5
    assert is_dca_phase_active(s) is True


def test_phase_inactive_when_all_days_done():
    s = default_state()
    s["enabled"] = True
    s["target_days"] = 20
    s["days_done"] = 20
    assert is_dca_phase_active(s) is False


# ---------------------------------------------------------------------------
# dca_should_trigger
# ---------------------------------------------------------------------------

def test_trigger_skips_when_disabled():
    s = default_state()
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=1_000_000)
    assert res is None


def test_trigger_skips_when_already_bought_today():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 3,
        "total_target_twd": 500_000, "twd_spent": 75_000,
        "symbol_priority": ["0050.TW"],
        "last_buy_date": "2026-04-29",
    })
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=1_000_000)
    assert res is None


def test_trigger_returns_action_for_active_phase():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 0,
        "total_target_twd": 500_000, "twd_spent": 0,
        "symbol_priority": ["0050.TW", "00878.TW"],
        "next_symbol_idx": 0,
    })
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=1_000_000)
    assert res is not None
    # 500k / 20 days = 25k/day
    assert res["amount_twd"] == 25000
    assert res["symbol"] == "0050.TW"
    assert res["day_index"] == 1
    assert res["of_total"] == 20
    assert res["next_symbol_idx"] == 1  # 下次輪到 00878


def test_trigger_capped_by_available_cash():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 0,
        "total_target_twd": 500_000, "twd_spent": 0,
        "symbol_priority": ["0050.TW"],
    })
    # cash 只有 5000，daily 25000 應該被截斷到 5000
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=5000)
    assert res is not None
    assert res["amount_twd"] == 5000


def test_trigger_returns_none_when_cash_too_small():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 0,
        "total_target_twd": 500_000, "twd_spent": 0,
        "symbol_priority": ["0050.TW"],
    })
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=50)
    assert res is None


def test_trigger_no_priority_returns_none():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 0,
        "total_target_twd": 500_000, "twd_spent": 0,
        "symbol_priority": [],   # 空清單
    })
    res = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=1_000_000)
    assert res is None


def test_trigger_rotates_through_symbols():
    """在不同天觸發應輪流 symbol。"""
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 0,
        "total_target_twd": 500_000, "twd_spent": 0,
        "symbol_priority": ["A", "B", "C"],
        "next_symbol_idx": 0,
    })
    r0 = dca_should_trigger(s, today=date(2026, 4, 29), available_cash=1_000_000)
    assert r0["symbol"] == "A" and r0["next_symbol_idx"] == 1

    s2 = dict(s, next_symbol_idx=1)
    r1 = dca_should_trigger(s2, today=date(2026, 4, 30), available_cash=1_000_000)
    assert r1["symbol"] == "B" and r1["next_symbol_idx"] == 2

    s3 = dict(s, next_symbol_idx=2)
    r2 = dca_should_trigger(s3, today=date(2026, 5, 1), available_cash=1_000_000)
    assert r2["symbol"] == "C" and r2["next_symbol_idx"] == 0


# ---------------------------------------------------------------------------
# record_dca_buy
# ---------------------------------------------------------------------------

def test_record_dca_buy_increments_state():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 5,
        "total_target_twd": 500_000, "twd_spent": 100_000,
        "symbol_priority": ["A", "B"],
    })
    new = record_dca_buy(s, today=date(2026, 4, 29), amount_twd=25_000, next_symbol_idx=1)
    assert new["days_done"] == 6
    assert new["twd_spent"] == 125_000
    assert new["last_buy_date"] == "2026-04-29"
    assert new["next_symbol_idx"] == 1
    assert new["completed"] is False


def test_record_dca_buy_completes_at_target():
    s = default_state()
    s.update({
        "enabled": True, "target_days": 20, "days_done": 19,
        "total_target_twd": 500_000, "twd_spent": 475_000,
        "symbol_priority": ["A"],
    })
    new = record_dca_buy(s, today=date(2026, 5, 19), amount_twd=25_000, next_symbol_idx=0)
    assert new["days_done"] == 20
    assert new["completed"] is True


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

def test_start_dca_writes_state(state_dir):
    s = start_dca(
        state_dir,
        total_target_twd=600_000,
        target_days=30,
        symbol_priority=["0050.TW", "00878.TW"],
        today=date(2026, 4, 29),
    )
    assert s["enabled"] is True
    assert s["total_target_twd"] == 600_000
    assert s["target_days"] == 30
    assert s["started_on"] == "2026-04-29"

    # 重新讀取也一致
    s2 = load_dca_state(state_dir)
    assert s2["enabled"] is True
    assert s2["symbol_priority"] == ["0050.TW", "00878.TW"]


def test_stop_dca_disables(state_dir):
    start_dca(state_dir, total_target_twd=600_000, target_days=30,
              symbol_priority=["A"], today=date(2026, 4, 29))
    s = stop_dca(state_dir)
    assert s["enabled"] is False
