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
