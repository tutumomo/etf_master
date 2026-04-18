# WorldMonitor × ETF_TW 整合設計文件

**日期：** 2026-04-19
**狀態：** 已核准，待實作
**作者：** ETF_Master + Claude Code

---

## 目標

將 worldmonitor 的全球信號整合進 etf_master，強化 AI 決策橋的輸入視野，並在重大事件發生時自動觸發保護機制。

涵蓋四個能力：
1. 全球供應鏈監控（chokepoints、航運壓力、關鍵礦物）
2. 突發危機偵測（衝突升級、地緣事件嚴重度）
3. 用戶偏好與現金流研究（透過 ETF 元資料動態曝險映射）
4. 跨時間因果關係（alerts JSONL 歷史積累）

---

## 架構決策

| 決策點 | 選擇 | 理由 |
|--------|------|------|
| 整合邊界 | 呼叫 worldmonitor Vercel endpoints（B 方案） | worldmonitor 已有 Railway → Redis → Vercel 快取層，直接消費已整合信號，CP 值最高 |
| 時效性 | 每日快照 + 事件驅動雙模式（C 方案） | 開盤前需要完整快照；盤中需要即時警報 |
| 整合深度 | 深度整合（C 方案） | 信號同時影響 AI 輸入層和 L1/L2/L3 事件判斷，可觸發鎖倉 |
| ETF 影響映射 | 動態推導（非靜態映射表） | 根據 ETF 元資料的 focus/index/地區動態計算曝險，watchlist 新增 ETF 自動納入 |

---

## State 架構

### 新增 State 檔案

```
instances/etf_master/state/
├── worldmonitor_snapshot.json      # 每日快照（07:50 更新）
└── worldmonitor_alerts.jsonl       # 即時警報（append-only）
```

### `worldmonitor_snapshot.json` 結構

```json
{
  "updated_at": "2026-04-19T07:50:00+08:00",
  "source": "worldmonitor",
  "supply_chain": {
    "global_stress_level": "moderate",
    "chokepoints": [
      {"name": "Strait of Hormuz", "status": "disrupted", "severity": 3}
    ],
    "shipping_stress_index": 0.72,
    "critical_minerals": {
      "taiwan_semiconductor_risk": "elevated"
    }
  },
  "geopolitical": {
    "global_risk_level": "elevated",
    "active_conflicts": 3,
    "highest_severity": "high",
    "taiwan_strait_risk": "low"
  },
  "macro": {
    "usd_index_trend": "strengthening",
    "energy_price_pressure": "moderate"
  }
}
```

### `worldmonitor_alerts.jsonl` 單筆結構

```json
{
  "timestamp": "2026-04-19T10:23:00+08:00",
  "alert_type": "supply_chain_disruption",
  "severity": "L2",
  "title": "Red Sea shipping route disrupted",
  "affected_etfs": ["00679B", "00687B"],
  "action_hint": "pause_auto_trade",
  "raw_source": "worldmonitor/supply-chain"
}
```

`severity` 對應現有事件等級：
- `L1` — 資訊性，不影響決策
- `L2` — 降低 AI 決策信心（`reduce_confidence`）
- `L3` — 觸發暫停自動交易（`pause_auto_trade`）

---

## 新增腳本：`sync_worldmonitor.py`

### 位置
`skills/ETF_TW/scripts/sync_worldmonitor.py`

### 雙模式

```
python sync_worldmonitor.py --mode daily   # 每日 pipeline 第 11 步
python sync_worldmonitor.py --mode watch   # 盤中每 30 分鐘
```

### 呼叫的 worldmonitor Endpoints

| 功能 | Endpoint | 對應 snapshot 欄位 |
|------|----------|-------------------|
| 供應鏈壓力 | `/api/supply-chain/status` | `supply_chain.*` |
| 衝突/危機 | `/api/conflicts/active` | `geopolitical.*` |
| 航運壓力 | `/api/shipping/stress` | `supply_chain.shipping_stress_index` |
| 關鍵礦物 | `/api/supply-chain/critical-minerals` | `supply_chain.critical_minerals.*` |

### 設定來源

worldmonitor base URL 存於 `instance_config.json`：

```json
{
  "worldmonitor": {
    "base_url": "https://your-worldmonitor.vercel.app",
    "enabled": true,
    "watch_interval_minutes": 30
  }
}
```

### 核心邏輯

**daily 模式：**
1. 呼叫 4 個 endpoints
2. 正規化成 `worldmonitor_snapshot.json` 格式
3. `atomic_save_json()` 寫入 instance state

**watch 模式：**
1. 呼叫相同 endpoints
2. 與上次快照比較，偵測 severity >= L2 的新事件
3. 有變化 → `safe_append_jsonl()` 寫入 `worldmonitor_alerts.jsonl`
4. 有 L3 事件 → 直接呼叫 `check_major_event_trigger.py`
5. 無變化 → 靜默退出

### ETF 動態曝險映射

**不使用靜態映射表。** 改為根據 watchlist 中每支 ETF 的元資料（`focus`、`index`、`name`）動態推導：

```python
RISK_DIMENSION_KEYWORDS = {
    "taiwan_strait_risk":       ["台灣", "台股", "加權", "0050", "006208"],
    "us_bond_risk":             ["美債", "公債", "bond", "00679B", "00687B"],
    "semiconductor_supply":     ["半導體", "科技", "semiconductor", "00830"],
    "energy_shock":             ["能源", "energy", "油"],
    "global_risk_high":         ["*"],  # 全部
}
```

掃描 watchlist 所有 ETF 的 `focus + index + name` 欄位，動態計算受影響清單。watchlist 新增任何 ETF 自動納入評估。

---

## 現有組件修改

### 1. `check_major_event_trigger.py`

**修改量：小（新增一個讀取路徑）**

```
現有 L1/L2/L3 判斷邏輯（RSS + market_event_context）
        +
讀取 worldmonitor_alerts.jsonl 最新未處理條目
        ↓
combined_event_level = max(現有等級, worldmonitor等級)
        ↓
L3 → major_event_flag.json（action: pause_auto_trade）
L2 → major_event_flag.json（action: reduce_confidence）
L1 → 僅記錄
```

### 2. `ai_decision_bridge.py`

**修改量：小（新增第 13 個輸入源）**

`ai_decision_request.json` 新增欄位：

```json
"worldmonitor_context": {
  "supply_chain_stress": "moderate",
  "geopolitical_risk": "elevated",
  "taiwan_strait_risk": "low",
  "active_alerts_count": 1,
  "highest_alert_severity": "L2",
  "affected_etf_signals": {
    "00830": {"semiconductor_supply": "disrupted"},
    "00679B": {"us_bond_risk": "elevated"}
  }
}
```

### 3. `dashboard/app.py`

**修改量：小（新增 1 個 API 路由 + 1 個 dashboard 卡片）**

新增 `/api/worldmonitor-status` endpoint，回傳 snapshot 摘要。

Dashboard overview 頁面新增全球風險雷達卡片：

```
┌─────────────────────────────────┐
│ 🌐 全球風險雷達                  │
│ 供應鏈壓力：moderate ⚠️          │
│ 地緣政治：elevated ⚠️            │
│ 台海風險：low ✅                  │
│ 航運壓力指數：0.72               │
│ 最近警報：1 筆（L2）             │
│ 更新：2026-04-19 07:50          │
└─────────────────────────────────┘
```

---

## Cron 新增任務

```yaml
# 每日開盤前快照（接在現有 pipeline 第 10 步之後）
- name: "worldmonitor 每日快照"
  schedule: "50 7 * * 1-5"        # 07:50 weekdays
  command: "sync_worldmonitor.py --mode daily"

# 盤中事件監控
- name: "worldmonitor 事件巡檢"
  schedule: "*/30 9-14 * * 1-5"   # 09:00-14:30 every 30min weekdays
  command: "sync_worldmonitor.py --mode watch"
```

---

## Refresh Pipeline 更新後順序

```
1.  sync_strategy_link.py
2.  sync_live_state.py / sync_paper_state.py
3.  sync_market_cache.py
4.  generate_market_event_context.py
5.  generate_taiwan_market_context.py
6.  check_major_event_trigger.py          ← 讀取 worldmonitor_alerts.jsonl
7.  sync_portfolio_snapshot.py
8.  sync_ohlcv_history.py
9.  generate_intraday_tape_context.py
10. sync_agent_summary.py
11. sync_worldmonitor.py --mode daily     ← 新增
```

---

## 跨時間因果關係

`worldmonitor_alerts.jsonl` 為 append-only，永不刪除。每筆 alert 記錄：
- 事件時間戳記
- 信號類型與嚴重度
- 受影響 ETF 清單

配合 `ai_decision_outcome.jsonl`（現有），未來可做：
- 信號發出後 T+1/T+3/T+10 ETF 報酬分析
- 識別哪類 worldmonitor 信號對台灣 ETF 有預測力
- 逐步建立跨時間因果模型（需 3-6 個月資料積累）

---

## 實作工作量估計

| 項目 | 新增/修改 | 估計複雜度 |
|------|-----------|-----------|
| `sync_worldmonitor.py` | 新增 | 中（~200 行） |
| `check_major_event_trigger.py` | 修改 | 小（+30 行） |
| `ai_decision_bridge.py` | 修改 | 小（+20 行） |
| `dashboard/app.py` | 修改 | 小（+50 行） |
| `dashboard/templates/overview.html` | 修改 | 小（+30 行） |
| cron/jobs.json | 修改 | 小（+2 entries） |
| instance_config.json schema | 修改 | 小（+5 行） |
| 測試檔案 | 新增 | 中（~100 行） |

**總計：約 450 行新增/修改，影響 7 個檔案。**

---

## 硬限制遵守

- `worldmonitor_snapshot.json` / `worldmonitor_alerts.jsonl` 為新增 state 檔，不覆蓋任何現有 truth 檔案
- watch 模式在非交易時段（非週一至週五 09:00-14:30）不執行
- worldmonitor 連線失敗時靜默降級（使用上次快照），不中斷現有 pipeline
- `instance_config.json` 中 `worldmonitor.enabled: false` 可完全停用整合
