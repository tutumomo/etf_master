"""
Tests for auto_trade.circuit_breaker
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts.auto_trade import circuit_breaker as cb
from scripts.auto_trade import pending_queue as pq

TW_TZ = ZoneInfo("Asia/Taipei")


@pytest.fixture
def state_dir(tmp_path):
    sd = tmp_path / "state"
    sd.mkdir()
    return sd


def _write(state_dir, name, payload):
    (state_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def test_master_switch_default_off(state_dir):
    config = cb.load_auto_trade_config(state_dir)
    res = cb.check_master_switch(config)
    assert res.passed is False
    assert "off" in res.detail or "False" in res.detail


def test_master_switch_enabled(state_dir):
    _write(state_dir, "auto_trade_phase2_config.json", {"enabled": True})
    config = cb.load_auto_trade_config(state_dir)
    res = cb.check_master_switch(config)
    assert res.passed is True


def test_market_risk_off_blocks(state_dir):
    _write(state_dir, "market_event_context.json", {
        "event_regime": "risk-off", "global_risk_level": "elevated",
    })
    res = cb.check_market_risk(state_dir)
    assert res.passed is False
    assert "risk-off" in res.detail


def test_market_risk_high_level_blocks(state_dir):
    _write(state_dir, "market_event_context.json", {
        "event_regime": "neutral", "global_risk_level": "high",
    })
    res = cb.check_market_risk(state_dir)
    assert res.passed is False


def test_market_risk_normal_passes(state_dir):
    _write(state_dir, "market_event_context.json", {
        "event_regime": "neutral", "global_risk_level": "low",
    })
    res = cb.check_market_risk(state_dir)
    assert res.passed is True


def test_major_event_triggered(state_dir):
    _write(state_dir, "major_event_flag.json", {
        "triggered": True, "level": "L3", "reason": "聯準會緊急降息",
    })
    res = cb.check_major_event(state_dir)
    assert res.passed is False
    assert "L3" in res.detail


def test_major_event_not_triggered(state_dir):
    _write(state_dir, "major_event_flag.json", {"triggered": False, "level": "none"})
    res = cb.check_major_event(state_dir)
    assert res.passed is True


def test_sensor_health_critical_failure(state_dir):
    _write(state_dir, "sensor_health.json", {
        "healthy": False, "critical_failures": ["portfolio", "market_cache"],
    })
    res = cb.check_sensor_health(state_dir)
    assert res.passed is False
    assert "portfolio" in res.detail


def test_sensor_health_ok(state_dir):
    _write(state_dir, "sensor_health.json", {"healthy": True, "critical_failures": []})
    res = cb.check_sensor_health(state_dir)
    assert res.passed is True


def test_sensor_health_missing_file_passes(state_dir):
    """初次部署 sensor_health.json 還沒產生 → 應放行（保守）"""
    res = cb.check_sensor_health(state_dir)
    assert res.passed is True


def test_weekly_loss_within_limit(state_dir):
    _write(state_dir, "daily_pnl.json", {"weekly_pnl_pct": -0.02})  # -2%
    res = cb.check_weekly_loss(state_dir, limit_pct=0.05)
    assert res.passed is True


def test_weekly_loss_exceeds_limit(state_dir):
    _write(state_dir, "daily_pnl.json", {"weekly_pnl_pct": -0.06})  # -6%
    res = cb.check_weekly_loss(state_dir, limit_pct=0.05)
    assert res.passed is False
    assert "-6" in res.detail.replace(".00", "")


def test_daily_buy_amount_within_limit(state_dir):
    queue_path = state_dir / "pending_auto_orders.json"
    history_path = state_dir / "auto_trade_history.jsonl"
    pq.enqueue(
        queue_path=queue_path, history_path=history_path,
        side="buy", symbol="0050", quantity=100, price=86,
        trigger_source="x", trigger_reason="y",
    )
    # 100*86 = 8600；可交割 100000，50% 上限 = 50000 → 通過
    res = cb.check_daily_buy_amount(queue_path, settlement_safe_cash=100000, daily_pct=0.5)
    assert res.passed is True


def test_daily_buy_amount_exceeds(state_dir):
    queue_path = state_dir / "pending_auto_orders.json"
    history_path = state_dir / "auto_trade_history.jsonl"
    pq.enqueue(
        queue_path=queue_path, history_path=history_path,
        side="buy", symbol="0050", quantity=1000, price=200,
        trigger_source="x", trigger_reason="y",
    )
    # 1000*200 = 200000；可交割 100000，50% = 50000 → 200000 > 50000 → 擋下
    res = cb.check_daily_buy_amount(queue_path, settlement_safe_cash=100000, daily_pct=0.5)
    assert res.passed is False


def test_daily_buy_amount_zero_settlement_safe_cash(state_dir):
    queue_path = state_dir / "pending_auto_orders.json"
    res = cb.check_daily_buy_amount(queue_path, settlement_safe_cash=0, daily_pct=0.5)
    assert res.passed is False
    assert "0" in res.detail


def test_consecutive_buy_days_under_limit(state_dir, monkeypatch):
    history_path = state_dir / "auto_trade_history.jsonl"
    today = datetime.now(tz=TW_TZ).date()
    # 寫 3 個過去日期的 executed buy
    lines = []
    for i in range(1, 4):
        d = (today - timedelta(days=i)).isoformat()
        lines.append(json.dumps({
            "_event": "status_changed_to_executed",
            "side": "buy",
            "created_at": f"{d}T09:30:00+08:00",
        }))
    history_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = cb.check_consecutive_buy_days(history_path, limit_days=5)
    # 3 < 5 → 通過
    assert res.passed is True


def test_consecutive_buy_days_at_limit(state_dir):
    history_path = state_dir / "auto_trade_history.jsonl"
    today = datetime.now(tz=TW_TZ).date()
    lines = []
    for i in range(1, 6):  # 前 5 日全有
        d = (today - timedelta(days=i)).isoformat()
        lines.append(json.dumps({
            "_event": "status_changed_to_executed",
            "side": "buy",
            "created_at": f"{d}T09:30:00+08:00",
        }))
    history_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = cb.check_consecutive_buy_days(history_path, limit_days=5)
    assert res.passed is False


# ---------------------------------------------------------------------------
# evaluate_buy_allowed (integration)
# ---------------------------------------------------------------------------

def test_evaluate_all_pass(state_dir):
    _write(state_dir, "auto_trade_phase2_config.json", {"enabled": True})
    _write(state_dir, "market_event_context.json", {"event_regime": "neutral", "global_risk_level": "low"})
    _write(state_dir, "major_event_flag.json", {"triggered": False})
    _write(state_dir, "sensor_health.json", {"healthy": True})
    _write(state_dir, "daily_pnl.json", {"weekly_pnl_pct": 0.01})

    result = cb.evaluate_buy_allowed(state_dir, settlement_safe_cash=100000)
    assert result.buy_allowed is True
    assert result.reasons == []
    # 7 個 check 全部 passed
    assert all(c.passed for c in result.checks)


def test_evaluate_master_switch_off_blocks(state_dir):
    _write(state_dir, "market_event_context.json", {"event_regime": "neutral"})
    _write(state_dir, "major_event_flag.json", {"triggered": False})
    # auto_trade_config 不存在 → enabled=False

    result = cb.evaluate_buy_allowed(state_dir, settlement_safe_cash=100000)
    assert result.buy_allowed is False
    assert any("master_switch" in r for r in result.reasons)


def test_evaluate_multiple_failures_listed(state_dir):
    _write(state_dir, "market_event_context.json", {
        "event_regime": "risk-off", "global_risk_level": "high",
    })
    _write(state_dir, "major_event_flag.json", {
        "triggered": True, "level": "L3", "reason": "test event",
    })

    result = cb.evaluate_buy_allowed(state_dir, settlement_safe_cash=100000)
    assert result.buy_allowed is False
    # 應該至少有 master_switch + market_risk + major_event 三個失敗
    assert len(result.reasons) >= 3
