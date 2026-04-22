"""
sensor_health.py — RESILIENCE-01

感測器分層健康檢查模組。
關鍵感測器失效 → healthy=False（呼叫方應中止管線）
輔助感測器缺失 → 累積 warning_prefix（呼叫方降級繼續）

Usage（獨立診斷）：
    AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TW_TZ = ZoneInfo("Asia/Taipei")

# ── 關鍵感測器定義 ────────────────────────────────────────────────────────────
# 格式：(sensor_name, filename, required_field_or_None)
# required_field：若非 None，dict 中必須有此 key 且值非空
CRITICAL_SENSORS: list[tuple[str, str, str | None]] = [
    ("portfolio",      "portfolio_snapshot.json",   "holdings"),
    ("market_cache",   "market_cache.json",          "quotes"),    # quotes 不能為空 {}
    ("market_context", "market_context_taiwan.json", "risk_temperature"),
]

# ── 輔助感測器定義 ────────────────────────────────────────────────────────────
# 格式：(sensor_name, filename)
AUXILIARY_SENSORS: list[tuple[str, str]] = [
    ("event_context",        "market_event_context.json"),
    ("tape_context",         "intraday_tape_context.json"),
    ("worldmonitor",         "worldmonitor_snapshot.json"),
    ("central_bank_calendar","central_bank_calendar.json"),
]


@dataclass
class SensorHealthResult:
    healthy: bool                          # False = 有關鍵感測器失效
    critical_failures: list[str] = field(default_factory=list)   # e.g. ["portfolio"]
    auxiliary_missing: list[str] = field(default_factory=list)   # e.g. ["event_context"]
    warning_prefix: str = ""               # "[資料不完整: event_context] " 或 ""
    checked_at: str = ""                   # ISO8601


def _load_sensor(path: Path) -> dict | None:
    """讀取感測器 JSON。失敗或空 dict 回傳 None。"""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


def _is_critical_ok(data: dict, required_field: str | None) -> bool:
    """關鍵感測器資料是否合格。"""
    if required_field is None:
        return True
    val = data.get(required_field)
    if val is None:
        return False
    # market_cache 的 quotes 不能是空 dict
    if isinstance(val, dict) and len(val) == 0:
        return False
    # holdings / quotes 不能是空 list
    if isinstance(val, list) and len(val) == 0:
        return False
    return True


def check_sensor_health(state_dir: Path) -> SensorHealthResult:
    """純函數：檢查所有感測器，回傳 SensorHealthResult。"""
    critical_failures: list[str] = []
    auxiliary_missing: list[str] = []

    for name, filename, required_field in CRITICAL_SENSORS:
        data = _load_sensor(state_dir / filename)
        if data is None or not _is_critical_ok(data, required_field):
            critical_failures.append(name)

    for name, filename in AUXILIARY_SENSORS:
        data = _load_sensor(state_dir / filename)
        if data is None:
            auxiliary_missing.append(name)

    healthy = len(critical_failures) == 0
    warning_prefix = ""
    if auxiliary_missing:
        missing_str = ", ".join(auxiliary_missing)
        warning_prefix = f"[資料不完整: {missing_str}] "

    return SensorHealthResult(
        healthy=healthy,
        critical_failures=critical_failures,
        auxiliary_missing=auxiliary_missing,
        warning_prefix=warning_prefix,
        checked_at=datetime.now(tz=TW_TZ).isoformat(),
    )
