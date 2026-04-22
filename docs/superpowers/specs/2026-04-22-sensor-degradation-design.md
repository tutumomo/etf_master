# Design: Sensor Degradation Framework（感測器降級框架）

Date: 2026-04-22

## 背景與動機

etf_master 的決策管線目前以 `safe_load_json` 靜默讀取所有感測器資料，任何感測器失效都只會回傳預設值，外部完全不可見。這導致：

- 報價掛掉時系統仍可能輸出買入決策（基於空 quotes）
- AI Bridge 讀到的 `risk_context_summary` 不知道資料是否完整
- Dashboard 無法顯示感測器健康狀態
- 事後復盤無法區分「決策品質差」vs「感測器資料不完整」

本設計引入兩層感測器分類與 partial degradation 機制，讓管線在資料不完整時能安全降級而非靜默出錯。

---

## 感測器分層

### 關鍵感測器（任一失效 → 管線中止）

| 感測器 | 檔案路徑 | 失效判定 |
|--------|---------|---------|
| `portfolio` | `state/portfolio_snapshot.json` | 不存在 / 解析失敗 / 空 dict / 缺 `holdings` 欄位 |
| `market_cache` | `state/market_cache.json` | 不存在 / 解析失敗 / 空 dict / 缺 `quotes` / `quotes` 為空 `{}` |
| `market_context` | `state/market_context_taiwan.json` | 不存在 / 解析失敗 / 空 dict / 缺 `risk_temperature` 欄位 |

### 輔助感測器（失效 → 降級繼續，標記警示）

| 感測器 | 檔案路徑 |
|--------|---------|
| `event_context` | `state/market_event_context.json` |
| `tape_context` | `state/intraday_tape_context.json` |
| `worldmonitor` | `state/worldmonitor_context.json` |
| `central_bank_calendar` | `state/central_bank_calendar.json` |

輔助感測器失效判定：檔案不存在 / JSON 解析失敗 / 內容為空 dict `{}`。欄位完整性不檢查（容忍度更高）。

---

## 架構：資料流

```
run_auto_decision_scan.main()
  │
  ├── 1. _check_sensor_health(state_dir)
  │       └── 回傳 SensorHealthResult
  │             ├── critical_failures 非空 → 寫 sensor_health.json + early return（不跑決策）
  │             └── auxiliary_missing 非空 → 累積 warning_prefix，繼續執行
  │
  ├── 2. 寫 state/sensor_health.json
  │
  ├── 3. 若有 auxiliary_missing：
  │       risk_context_summary = warning_prefix + original_summary
  │
  └── 4. 繼續原有 decide_action() → resolve_consensus() → ...

check_sensor_health.py（獨立 CLI）
  └── 讀 state/sensor_health.json → 印人類可讀報告
```

---

## 新增檔案

### `scripts/sensor_health.py`

核心純函數模組。

```python
@dataclass
class SensorHealthResult:
    healthy: bool                  # False = 有關鍵感測器失效
    critical_failures: list[str]   # e.g. ["portfolio", "market_cache"]
    auxiliary_missing: list[str]   # e.g. ["event_context", "worldmonitor"]
    warning_prefix: str            # "[資料不完整: event_context, worldmonitor] " 或 ""
    checked_at: str                # ISO8601
```

**對外 API：**

```python
def check_sensor_health(state_dir: Path) -> SensorHealthResult:
    """純函數：檢查所有感測器，回傳健康狀態。"""
```

### `scripts/check_sensor_health.py`

獨立 CLI 診斷腳本。

```
Usage: AGENT_ID=etf_master .venv/bin/python3 scripts/check_sensor_health.py

Output example:
  [SENSOR HEALTH] 2026-04-22T10:05:00+08:00
  ✅ 關鍵感測器：全部正常
  ⚠️  輔助感測器缺失：event_context, worldmonitor
  → 管線將降級執行，risk_context_summary 已標記警示
```

### `state/sensor_health.json`（自動產生）

```json
{
  "healthy": true,
  "critical_failures": [],
  "auxiliary_missing": ["event_context"],
  "warning_prefix": "[資料不完整: event_context] ",
  "checked_at": "2026-04-22T10:00:00+08:00"
}
```

### `tests/test_sensor_health.py`

純函數單元測試，使用 `tmp_path` fixture，不依賴真實 state 目錄。

---

## 修改檔案

### `scripts/run_auto_decision_scan.py`

在 `main()` 的最前段（config/strategy 讀取之後，`decide_action()` 之前）加入：

```python
from sensor_health import check_sensor_health
from etf_core.state_io import atomic_save_json

health = check_sensor_health(STATE)
atomic_save_json(STATE / 'sensor_health.json', asdict(health))

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
```

---

## 測試策略

| 測試案例 | 驗證重點 |
|---------|---------|
| 全部感測器正常 | `healthy=True`，`critical_failures=[]`，`warning_prefix=""` |
| `portfolio.json` 不存在 | `healthy=False`，`critical_failures=["portfolio"]` |
| `market_cache.quotes` 為空 `{}` | `healthy=False`，`critical_failures=["market_cache"]` |
| `market_context` 缺 `risk_temperature` | `healthy=False`，`critical_failures=["market_context"]` |
| `event_context.json` 不存在 | `healthy=True`，`auxiliary_missing=["event_context"]`，`warning_prefix` 含警示字串 |
| 2 個輔助感測器缺失 | `auxiliary_missing` 長度 2，`warning_prefix` 含兩個名稱 |
| 關鍵 + 輔助同時失效 | `healthy=False`，兩個 list 各自正確填入 |

---

## 錯誤處理

| 失敗點 | 處理方式 |
|--------|---------|
| `sensor_health.json` 寫入失敗 | try/except + warning，不阻斷管線（健康檢查本身不能成為單點故障） |
| `check_sensor_health.py` 讀不到 json | 印 `[UNKNOWN]` 狀態，exit code 0（診斷腳本不影響生產） |
| 新增感測器需要加入分層 | 在 `sensor_health.py` 的 `CRITICAL_SENSORS` / `AUXILIARY_SENSORS` 常數 list 修改，無需改其他檔案 |

---

## 成功指標

- 關鍵感測器失效時，`run_auto_decision_scan` 輸出 `AUTO_DECISION_SCAN_CRITICAL_SENSOR_FAIL:*` 並 return 1
- 輔助感測器缺失時，`ai_decision_request.json` 的 `risk_context_summary` 含 `[資料不完整:*]` 前綴
- `state/sensor_health.json` 每次掃描後存在且格式正確
- `check_sensor_health.py` 可獨立執行並輸出可讀報告
- 全套測試（含新增 7 個）通過，現有 397 個測試無 regression
