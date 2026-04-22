from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sensor_health import check_sensor_health, SensorHealthResult


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_all_sensors_healthy(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    _write(state / "market_event_context.json", {"global_risk_level": "low"})
    _write(state / "intraday_tape_context.json", {"market_bias": "neutral"})
    _write(state / "worldmonitor_snapshot.json", {"alerts": []})
    _write(state / "central_bank_calendar.json", {"events": []})

    result = check_sensor_health(state)
    assert result.healthy is True
    assert result.critical_failures == []
    assert result.auxiliary_missing == []
    assert result.warning_prefix == ""

    # checked_at must be a timezone-aware ISO8601 string
    from datetime import datetime
    dt = datetime.fromisoformat(result.checked_at)
    assert dt.tzinfo is not None


def test_portfolio_missing(tmp_path):
    state = tmp_path / "state"
    # portfolio_snapshot.json does not exist
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "portfolio" in result.critical_failures


def test_market_cache_empty_quotes(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {}})   # empty quotes dict
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "market_cache" in result.critical_failures


def test_market_context_missing_risk_temperature(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"market_regime": "bull"})  # no risk_temperature
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "market_context" in result.critical_failures


def test_event_context_missing_is_auxiliary(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    # event_context.json does not exist — should be auxiliary only
    result = check_sensor_health(state)
    assert result.healthy is True
    assert "event_context" in result.auxiliary_missing
    assert "[資料不完整:" in result.warning_prefix
    assert "event_context" in result.warning_prefix


def test_two_auxiliary_missing(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    # event_context + worldmonitor missing; tape and central_bank present
    _write(state / "intraday_tape_context.json", {"market_bias": "neutral"})
    _write(state / "central_bank_calendar.json", {"events": []})
    result = check_sensor_health(state)
    assert result.healthy is True
    assert len(result.auxiliary_missing) == 2
    assert "event_context" in result.auxiliary_missing
    assert "worldmonitor" in result.auxiliary_missing


def test_critical_and_auxiliary_both_fail(tmp_path):
    state = tmp_path / "state"
    # portfolio missing (critical), event_context missing (auxiliary)
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "portfolio" in result.critical_failures
    assert "event_context" in result.auxiliary_missing
