---
name: etf-tw-worldmonitor-daily-patrol
description: WorldMonitor 每日事件巡檢 cron 巡邏流程。適用於 cron 自動觸發或手動檢查全球風險事件變化。
tags: [cron, worldmonitor, patrol, daily]
---

# WorldMonitor 每日事件巡檢

## 何時使用
- Cron 排程觸發 worldmonitor_daily 任務
- 手動檢查全球風險事件有無變化
- 需要產出結構化風險摘要報告

## 執行步驟（固定順序）

### 1. 執行每日同步
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW && \
AGENT_ID=etf_master .venv/bin/python3 scripts/sync_worldmonitor.py --mode daily 2>&1
```
確認輸出包含 `✓ 每日快照已更新`。

### 2. 讀取快照風險指標
檔案：`instances/etf_master/state/worldmonitor_snapshot.json`

必讀欄位：
- `updated_at` — 資料時效
- `supply_chain.global_stress_level` — 供應鏈壓力等級
- `supply_chain.chokepoints[]` — 各咽喉要道 status / disruptionScore / warRiskTier / description
- `geopolitical.global_risk_level` — 地緣風險
- `geopolitical.taiwan_strait_risk` — 台海風險
- `macro.*` — 宏觀指標

**報告輸出技巧**：chokepoints 表格只列出非 green 狀態的要道（節省篇幅），其餘用「其餘 N 條均 green」帶過。

### 3. 檢查重大事件旗標
檔案：`instances/etf_master/state/major_event_flag.json`

關鍵欄位：
- `triggered` — 是否觸發 L3 重大事件
- `level` / `category` — 事件分類
- `checked_at` — 檢查時效

### 2.5. 檢查 recent alerts 日誌（可選）
檔案：`instances/etf_master/state/worldmonitor_alerts.jsonl`

讀取最後幾行，檢查近期是否有 L2/L3 升級事件。若 alerts 全為空行或異常格式（level/category 缺失），可略過。

### 4. 檢查市場事件（event context 衍生）
檔案：`instances/etf_master/state/market_event_context.json`

關鍵欄位：
- `active_events[]` — 關注事件列表
- `event_regime` / `global_risk_level` / `defensive_bias`
- `summary` — 一句話摘要

### 5. 驗證 AI 決策鏈 worldmonitor 注入
檔案：`instances/etf_master/state/ai_decision_request.json`

檢查 `inputs.worldmonitor_context` 是否存在且包含：
- `supply_chain_stress`, `geopolitical_risk`, `taiwan_strait_risk`
- `active_alerts_count`, `highest_alert_severity`

### 6. 驗證 AI 推理是否實際引用（P2 缺口檢查）
檔案：`instances/etf_master/state/ai_decision_response.json`

檢查 `reasoning.risk_context_summary` 是否非空。
- **若為空**：worldmonitor 信號僅進 request 未進推理 → 標記 P2「假接線」缺口
- 這是反覆出現的已知問題，每次巡檢都應驗證

### 7. 產出結構化摘要報告

格式：
```
## 🌐 WorldMonitor 每日事件巡檢 — YYYY-MM-DD HH:MM

### 風險總覽（表格：指標 / 等級 / 備註）

### 海上咽喉要道現況（表格：要道 / 狀態 / 干擾分 / 戰爭風險 / 說明）

### 重大事件旗標（triggered? level? alerts count?）

### 市場事件（active_events 列表）

### AI 決策鏈狀態（worldmonitor 注入? risk_context_summary 非空?）

### 巡檢結論（3-5 點，含 P2 缺口提醒若適用）
```

## 輸出密度
- 這是 cron 巡檢，回覆應為精簡結構化報告
- 不給 A/B/C 選項
- 若無新事件且風險等級與前次相同，可考慮 [SILENT]

## 已知缺口（持久追蹤）

### P2: risk_context_summary 假接線（間歇性）
- `ai_decision_request.inputs.worldmonitor_context` 有值 ✓
- `ai_decision_response.reasoning.risk_context_summary` 有時為空 ✗（間歇出現）
- 意義：worldmonitor 信號進了 request，但 AI 推理有時未實際引用
- 2026-04-22 巡檢觀察到 risk_context_summary 已包含 worldmonitor 引用（供應鏈=high/地緣=high/台海=moderate），缺口暫時修復
- 每次巡檢仍應檢查此欄位，確認是否穩定修復

## 檔案路徑速查
- 同步腳本：`skills/ETF_TW/scripts/sync_worldmonitor.py`
- 快照：`skills/ETF_TW/instances/etf_master/state/worldmonitor_snapshot.json`
- 世界監控警報日誌：`skills/ETF_TW/instances/etf_master/state/worldmonitor_alerts.jsonl`
- 事件旗標：`skills/ETF_TW/instances/etf_master/state/major_event_flag.json`
- 事件上下文：`skills/ETF_TW/instances/etf_master/state/market_event_context.json`
- AI 請求：`skills/ETF_TW/instances/etf_master/state/ai_decision_request.json`
- AI 回應：`skills/ETF_TW/instances/etf_master/state/ai_decision_response.json`
- 決策共識：`skills/ETF_TW/instances/etf_master/state/decision_consensus.json`

> ⚠️ 路徑前置為 `~/.hermes/profiles/etf_master/`，完整範例：
> `~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/worldmonitor_snapshot.json`
> 若用 `read_file` 工具讀取，路徑中的 `instances/` 必須包含 `skills/ETF_TW/` 前綴，否則會得到 File not found。

## JSON 檔案讀取陷阱

**不要用 `read_file` + `json.loads`**：`read_file` 回傳含行號前綴（如 `1|{`），直接 `json.loads` 會因前綴而解析失敗。

**不要用 `terminal` 內嵌 Python**：f-string 雙層大括號 + shell 引號巢狀轉義會產生 `SyntaxError: empty expression not allowed`。

**正確做法**：用 `write_file` 寫一段簡短 Python 腳本到 `/tmp/wm_check.py`，再用 `terminal("python3 /tmp/wm_check.py")` 執行。範例：

```python
import json
base = "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/"
d = json.load(open(base + "worldmonitor_snapshot.json"))
# ... extract fields and print
```

此模式也適用於其他需要讀取 ETF_TW state JSON 的 cron 任務。