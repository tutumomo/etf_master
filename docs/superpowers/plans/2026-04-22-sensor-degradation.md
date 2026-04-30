# Sensor Degradation Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將決策管線的感測器分為「關鍵」和「輔助」兩層，關鍵感測器失效時中止管線，輔助感測器失效時降級繼續並標記警示，讓 partial degradation 可見而非靜默。

**Architecture:** 新增純函數模組 `sensor_health.py` 封裝分層檢查邏輯，`run_auto_decision_scan.py` 的 `main()` 在 `decide_action()` 前呼叫它；結果寫入 `state/sensor_health.json` 供 dashboard 讀取，輔助感測器缺失時將警示前綴注入 `market_context['context_summary']`，讓 AI Bridge 感知資料不完整。

**Tech Stack:** Python 3.14, dataclasses, pathlib, zoneinfo, etf_core.state_io, pytest

---

## File Map

| 動作 | 路徑 | 職責 |
|------|------|------|
| Create | `skills/ETF_TW/scripts/sensor_health.py` | `SensorHealthResult` dataclass + `check_sensor_health()` 純函數 |
| Create | `skills/ETF_TW/scripts/check_sensor_health.py` | 獨立 CLI 診斷腳本 |
| Create | `skills/ETF_TW/tests/test_sensor_health.py` | 純函數單元測試（7 個案例） |
| Modify | `skills/ETF_TW/scripts/run_auto_decision_scan.py` | `main()` 加入感測器健康檢查 + early return + 警示注入 |

---

## Task 1：`sensor_health.py` — 純函數核心

**Files:**
- Create: `skills/ETF_TW/scripts/sensor_health.py`
- Create: `skills/ETF_TW/tests/test_sensor_health.py`

- [ ] **Step 1: 建立測試檔，寫第一個失敗測試**

```python
# skills/ETF_TW/tests/test_sensor_health.py
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
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sensor_health.py::test_all_sensors_healthy -v
```
Expected: `ModuleNotFoundError: No module named 'sensor_health'`

- [ ] **Step 3: 建立 `sensor_health.py`**

```python
# skills/ETF_TW/scripts/sensor_health.py
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sensor_health.py::test_all_sensors_healthy -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/sensor_health.py \
        skills/ETF_TW/tests/test_sensor_health.py
git commit -m "feat(resilience): sensor_health.py — SensorHealthResult + check_sensor_health"
```

---

## Task 2：其餘 6 個測試案例

**Files:**
- Modify: `skills/ETF_TW/tests/test_sensor_health.py`

- [ ] **Step 1: 新增 6 個測試**

```python
# 加到 test_sensor_health.py（test_all_sensors_healthy 之後）

def test_portfolio_missing(tmp_path):
    state = tmp_path / "state"
    # portfolio_snapshot.json 不存在
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "portfolio" in result.critical_failures


def test_market_cache_empty_quotes(tmp_path):
    state = tmp_path / "state"
    _write(state / "portfolio_snapshot.json", {"holdings": [{"symbol": "0050"}]})
    _write(state / "market_cache.json", {"quotes": {}})   # empty quotes
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
    # event_context.json 不存在
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
    # event_context + worldmonitor 都不存在，tape 和 central_bank 存在
    _write(state / "intraday_tape_context.json", {"market_bias": "neutral"})
    _write(state / "central_bank_calendar.json", {"events": []})
    result = check_sensor_health(state)
    assert result.healthy is True
    assert len(result.auxiliary_missing) == 2
    assert "event_context" in result.auxiliary_missing
    assert "worldmonitor" in result.auxiliary_missing


def test_critical_and_auxiliary_both_fail(tmp_path):
    state = tmp_path / "state"
    # portfolio 不存在（關鍵），event_context 不存在（輔助）
    _write(state / "market_cache.json", {"quotes": {"0050": {"current_price": 150}}})
    _write(state / "market_context_taiwan.json", {"risk_temperature": "normal"})
    result = check_sensor_health(state)
    assert result.healthy is False
    assert "portfolio" in result.critical_failures
    assert "event_context" in result.auxiliary_missing
```

- [ ] **Step 2: 跑全部測試確認通過**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_sensor_health.py -v
```
Expected: `7 passed`

- [ ] **Step 3: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/tests/test_sensor_health.py
git commit -m "feat(resilience): sensor_health — 完整 7 個測試案例通過"
```

---

## Task 3：`check_sensor_health.py` — CLI 診斷腳本

**Files:**
- Create: `skills/ETF_TW/scripts/check_sensor_health.py`

- [ ] **Step 1: 建立 CLI 腳本**

```python
# skills/ETF_TW/scripts/check_sensor_health.py
"""
check_sensor_health.py — 獨立診斷 CLI

讀取 state/sensor_health.json（由 run_auto_decision_scan 產生），
印出人類可讀的健康狀態報告。

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py

Exit codes:
    0 — 正常或降級（只有輔助感測器缺失）
    0 — sensor_health.json 不存在（印 UNKNOWN 但不報錯）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etf_core import context
from etf_core.state_io import safe_load_json


def main() -> int:
    state_dir = context.get_state_dir()
    health = safe_load_json(state_dir / "sensor_health.json", {})

    if not health:
        print("[SENSOR HEALTH] UNKNOWN — sensor_health.json 不存在或為空")
        print("請先執行一次 run_auto_decision_scan 以產生健康狀態快照")
        return 0

    checked_at = health.get("checked_at", "unknown")
    healthy = health.get("healthy", False)
    critical = health.get("critical_failures", [])
    auxiliary = health.get("auxiliary_missing", [])

    print(f"[SENSOR HEALTH] {checked_at}")

    if healthy:
        print("✅ 關鍵感測器：全部正常")
    else:
        failed = ", ".join(critical)
        print(f"🚨 關鍵感測器失效：{failed}")
        print("   → 管線已中止，不跑決策")

    if auxiliary:
        missing = ", ".join(auxiliary)
        print(f"⚠️  輔助感測器缺失：{missing}")
        print("   → 管線降級執行，risk_context_summary 已標記警示")
    else:
        print("✅ 輔助感測器：全部正常")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 手動驗證腳本可執行**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py
```
Expected（sensor_health.json 尚不存在時）:
```
[SENSOR HEALTH] UNKNOWN — sensor_health.json 不存在或為空
請先執行一次 run_auto_decision_scan 以產生健康狀態快照
```

- [ ] **Step 3: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/check_sensor_health.py
git commit -m "feat(resilience): check_sensor_health.py — CLI 診斷腳本"
```

---

## Task 4：`run_auto_decision_scan.py` — 接入感測器健康檢查

**Files:**
- Modify: `skills/ETF_TW/scripts/run_auto_decision_scan.py`

- [ ] **Step 1: 確認整合點行號**

```bash
grep -n "if config.get.*trading_hours_only\|result = decide_action\|if not enabled" \
  ~/.hermes/profiles/etf_master/skills/ETF_TW/scripts/run_auto_decision_scan.py
```
Expected: 顯示 `if not enabled`（約 728 行）、`trading_hours_only`（約 735 行）、`result = decide_action`（約 741 行）的行號。

- [ ] **Step 2: 在 imports 區加入 sensor_health**

在 `run_auto_decision_scan.py` 頂部 import 區（`from ai_decision_bridge import ...` 之後）加入：

```python
from dataclasses import asdict
from sensor_health import check_sensor_health
```

- [ ] **Step 3: 在 `decide_action()` 呼叫前插入健康檢查**

找到這段（約 738-741 行）：

```python
    if config.get('trading_hours_only', True) and not market_open:
        state['lock_reason'] = '非交易時段，已自動停用'
        atomic_save_json(STATE_PATH, state)
        print('AUTO_DECISION_SCAN_OK:LOCKED')
        return 0

    result = decide_action(strategy, watchlist, market_cache, portfolio, market_context, event_context, tape_context)
```

改為：

```python
    if config.get('trading_hours_only', True) and not market_open:
        state['lock_reason'] = '非交易時段，已自動停用'
        atomic_save_json(STATE_PATH, state)
        print('AUTO_DECISION_SCAN_OK:LOCKED')
        return 0

    # ── 感測器健康檢查 ──────────────────────────────────────────────────────
    health = check_sensor_health(STATE)
    try:
        atomic_save_json(STATE / 'sensor_health.json', asdict(health))
    except Exception as _e:
        print(f'[sensor_health] sensor_health.json 寫入失敗（{_e}），繼續執行')

    if not health.healthy:
        state['lock_reason'] = f'關鍵感測器失效：{", ".join(health.critical_failures)}'
        atomic_save_json(STATE_PATH, state)
        print(f'AUTO_DECISION_SCAN_CRITICAL_SENSOR_FAIL:{",".join(health.critical_failures)}')
        return 1

    if health.warning_prefix:
        market_context = dict(market_context)
        market_context['context_summary'] = (
            health.warning_prefix + str(market_context.get('context_summary') or '')
        )
    # ───────────────────────────────────────────────────────────────────────

    result = decide_action(strategy, watchlist, market_cache, portfolio, market_context, event_context, tape_context)
```

- [ ] **Step 4: 跑全套測試確認無 regression**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `≥ 404 passed`（397 原有 + 7 新增），0 failed

- [ ] **Step 5: Commit**

```bash
cd ~/.hermes/profiles/etf_master
git add skills/ETF_TW/scripts/run_auto_decision_scan.py
git commit -m "feat(resilience): run_auto_decision_scan 接入感測器健康檢查"
```

---

## Task 5：端對端驗證 + CLAUDE.md + tag v1.4.9

- [ ] **Step 1: 手動 dry-run 驗證**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py
```

若 `state/sensor_health.json` 已存在（上次 scan 產生），預期看到健康報告；若不存在看到 UNKNOWN 提示，兩種都正常。

- [ ] **Step 2: 更新 CLAUDE.md**

在 `CLAUDE.md` 的 Important Rules for Code Changes 區塊（第 19 條之後）加入：

```
20. **感測器分層**：`sensor_health.py` 定義關鍵/輔助感測器清單（`CRITICAL_SENSORS` / `AUXILIARY_SENSORS`）。新增感測器時只需修改這兩個常數，無需改其他檔案。`state/sensor_health.json` 由 `run_auto_decision_scan` 自動產生，不要手動編輯。
```

- [ ] **Step 3: 跑全套測試最終確認**

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```
Expected: `≥ 404 passed`，0 failed

- [ ] **Step 4: 最終 commit + tag**

```bash
cd ~/.hermes/profiles/etf_master
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
feat(resilience): Sensor Degradation Framework — v1.4.9

- sensor_health.py：關鍵/輔助感測器分層，pure function，7 個測試
- check_sensor_health.py：獨立 CLI 診斷腳本
- run_auto_decision_scan.py：感測器失效時 early return，輔助缺失時注入警示前綴
- state/sensor_health.json：每次掃描寫入，供 dashboard 讀取

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git tag v1.4.9
```
