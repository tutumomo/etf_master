# AI Decision Bridge 設計文件

## 目的

AI Decision Bridge 不是單純把一段 AI 文字顯示到 dashboard 上，而是作為 ETF_TW 未來自主決策系統的中樞接口。

其目標是讓系統逐步從：
- 規則型 preview engine
- 進化到可感知、可建議、可留存、可複盤、可持續改進
- 最終在成熟條件下，才進入受控自主決策與自主下單權限

---

## 核心定位

AI Decision Bridge = Dashboard / State / AI Agent 之間的正式橋接層。

它負責：
1. 將可驗證的市場 / 持倉 / 風險 / 狀態背景整理成 request state
2. 讓 AI Agent 讀取 request state 後生成可審核的 decision artifact
3. 將 decision artifact 回寫為 response state
4. 讓 dashboard / agent / review pipeline 共用同一份 AI 建議結果
5. 為後續 outcome review / reflection / strategy iteration 提供基礎資料結構

---

## 長期演進路線圖

### Stage 0：現況（規則型 preview / state 顯示）
- 規則型 auto decision / preview engine
- dashboard 顯示 state
- callback / polling / fills / reconciliation 主幹建立中

### Stage 1：AI 建議橋接
- dashboard / scripts 寫出 `ai_decision_request.json`
- AI Agent 讀取 request state
- AI Agent 寫出 `ai_decision_response.json`
- dashboard 顯示 AI 建議
- 不自動下單

### Stage 2：建議留存 + outcome review
- 每次 AI 建議都留存 request / response / outcome / reflection
- 後續可對比建議與市場結果
- 支援 decision quality review

### Stage 3：受控自主
- 允許 AI 自主建立 preview
- 允許 AI 自主補風險標籤 / 候選排序 / 重新掃描請求
- 仍不直接 live submit

### Stage 4：成熟後自主下單
- 僅在風控、交易時段真相源、broker reconciliation、decision review 機制成熟後，才考慮有限自主下單權限

---

## 設計原則

### 原則 1：Dashboard 不直接依賴 AI 在線 RPC
Dashboard 只讀 state，不直接同步 call AI。

原因：
- AI 可能不在線
- AI 可能回應過慢
- AI 可能回空或失敗
- 直接 RPC 會讓前端過度脆弱

### 原則 2：AI 建議必須是 decision artifact，而不是一次性文字
每次 AI 建議都要有：
- 生成時間
- 使用的 context version
- 依據來源
- 決策理由
- 風險 / 限制
- 不確定性
- freshness / stale 資訊

### 原則 3：持倉真相、委託真相、成交真相必須與 AI 建議分層
- `positions.json` = 持倉真相
- `orders_open.json` = 未終局委託真相
- `fills_ledger.json` = 成交事實記錄
- AI 建議 = decision layer

AI 建議不可以反過來覆蓋真相源。

### 原則 4：自主下單是最後階段，不是第一階段
必須先有：
- 可審核的建議
- 可追溯的結果
- 可檢討的決策品質
- 可對齊的 broker / fills / positions 主幹

之後才談 live auto submit。

---

## State Contract 設計

### 1. `ai_decision_request.json`

#### 目的
由 dashboard / script 產生，作為 AI Agent 的輸入請求。

#### 建議欄位
```json
{
  "request_id": "string",
  "created_at": "ISO timestamp",
  "requested_by": "dashboard|agent|system",
  "mode": "preview_only|research_only|decision_only",
  "context_version": "string",
  "context_updated_at": "ISO timestamp",
  "inputs": {
    "strategy": {},
    "positions": {},
    "orders_open": {},
    "fills_ledger": {},
    "portfolio_snapshot": {},
    "market_cache": {},
    "market_intelligence": {},
    "intraday_tape_context": {},
    "market_context_taiwan": {},
    "market_event_context": {},
    "market_calendar_status": {},
    "reconciliation": {},
    "decision_memory_context": {},
    "worldmonitor_context": {
      "supply_chain_stress": "low|moderate|elevated|high|critical",
      "geopolitical_risk": "low|moderate|elevated|high|critical",
      "taiwan_strait_risk": "low|moderate|elevated|high|critical",
      "active_alerts_count": 0,
      "highest_alert_severity": "L1|L2|L3|none",
      "affected_etf_signals": []
    }
  }
}
```

### 2. `ai_decision_response.json`

#### 目的
AI Agent 產出的正式 decision artifact，由 dashboard / agent / review pipeline 共用。

#### 建議欄位
```json
{
  "request_id": "string",
  "generated_at": "ISO timestamp",
  "expires_at": "ISO timestamp",
  "stale": false,
  "source": "ai_decision_bridge",
  "agent": {
    "name": "ETF_Master",
    "version": "string"
  },
  "decision": {
    "summary": "string",
    "action": "hold|preview_buy|preview_sell|watch_only",
    "confidence": "low|medium|high",
    "uncertainty": "string",
    "strategy_alignment": "string"
  },
  "candidate": {
    "symbol": "string",
    "side": "buy|sell|hold",
    "reference_price": 0,
    "quantity": 0,
    "reason": "string",
    "risk_note": "string"
  },
  "reasoning": {
    "market_context_summary": "string",
    "position_context_summary": "string",
    "risk_context_summary": "string"
  },
  "warnings": [],
  "input_refs": {
    "positions": "positions.json",
    "orders_open": "orders_open.json",
    "fills_ledger": "fills_ledger.json",
    "market_intelligence": "market_intelligence.json"
  }
}
```

### 3. `ai_decision_outcome.jsonl` / review ledger

#### 目的
將每次 AI 建議與其後續市場結果、人工評價、策略修正連結起來。

#### 建議欄位
- request_id
- response_id（若需要）
- review_at
- outcome_status
- outcome_note
- pnl_context（若適用）
- human_feedback
- rule_update_needed

---

## 執行流程

### Step 1：Dashboard / Script 產生 request
- dashboard refresh 後或特定操作觸發
- 將最新 state 整理為 `ai_decision_request.json`

### Step 2：AI Agent 消費 request
- AI Agent 檢查 request
- 讀取 state inputs
- 視需要調用金融技能
- 生成 decision artifact

### Step 3：AI Agent 寫回 response
- 寫入 `ai_decision_response.json`
- 標記 freshness / stale / expires_at

### Step 4：Dashboard 顯示 response
- 若 response fresh：顯示 AI 建議
- 若 stale：顯示上次 AI 建議 + stale 提示
- 若無 response：fallback 到規則型 preview engine 或顯示等待 AI

### Step 5：後續 review / reflection
- outcome pipeline 根據後續市場結果與人工回饋補 review
- 為將來的策略調整與 decision quality 提供素材

---

## Fallback 規則

### 1. AI 不在線
Dashboard 顯示：
- 上次有效建議（若存在）
- 或 fallback 到規則型 preview engine
- 並標記 `AI unavailable`

### 2. AI 回空 / 失敗
- 保留最後有效 `ai_decision_response.json`
- 顯示 warning
- 不讓 UI 整塊空掉

### 3. Response 過期
- 顯示 stale badge
- 顯示 `generated_at` / `expires_at`
- 視需要提醒重新生成

---

## Freshness / Stale 規則

### 建議欄位
- `generated_at`
- `context_updated_at`
- `expires_at`
- `stale`

### 建議原則
- 盤中 AI 建議應有較短有效期
- 休市 / 盤後可較長
- 一旦 context 與 response 時差過大，就應顯示 stale

---

## 風控與權限分層

### AI Decision Bridge 初期權限
- 可讀 state
- 可寫 request / response / review state
- 可產生建議
- 不可直接 live submit

### 受控自主前提
必須先具備：
- Market Session Truth Source
- Broker reconciliation 完整
- fills / positions close-the-loop
- decision quality review 機制
- stale / fallback / error handling 完整

### 未來自主下單前提
- decision artifact 穩定
- review outcome 有足夠樣本
- 風控 gating 明確
- 人工可審核 / 可回滾 / 可停用

---

## Worldmonitor 全球風險信號整合（v1.4.0）

### 第 14 個輸入源：`worldmonitor_context`

`ai_decision_request.json` 的 `inputs.worldmonitor_context` 由 `generate_ai_decision_request.py` 從以下兩個 state 檔案組合生成：

| 來源檔案 | 說明 |
|---|---|
| `worldmonitor_snapshot.json` | 每日快照，供應鏈/地緣/宏觀風險等級 |
| `worldmonitor_alerts.jsonl` | 最近 2 小時內的 L2/L3 升級事件 |

組合邏輯由 `scripts/ai_decision_bridge.py` 的 `_build_worldmonitor_context()` 執行：

```python
{
  "supply_chain_stress": snapshot.supply_chain.global_stress_level,
  "geopolitical_risk":   snapshot.geopolitical.global_risk_level,
  "taiwan_strait_risk":  snapshot.geopolitical.taiwan_strait_risk,
  "active_alerts_count": len(recent_alerts),
  "highest_alert_severity": max(alerts.severity) or "none",
  "affected_etf_signals": union(alert.affected_etfs for alert in recent_alerts)
}
```

### AI 如何使用此信號

- **`supply_chain_stress` ≥ elevated** → 半導體相關 ETF（00830 等）建議調降 confidence
- **`geopolitical_risk` ≥ high** → 所有台股 ETF 建議 `watch_only`，暫停 preview_buy
- **`taiwan_strait_risk` ≥ elevated** → `action_hint: pause_auto_trade`，台股部位風險提醒
- **L3 alert 存在** → `check_major_event_trigger.py` 已自動觸發，decision engine 應優先採納最新 event context

### 資料流

```
worldmonitor API
    ↓ (sync_worldmonitor.py --mode daily/watch)
worldmonitor_snapshot.json / worldmonitor_alerts.jsonl
    ↓ (generate_ai_decision_request.py)
ai_decision_request.json → inputs.worldmonitor_context
    ↓ (AI Agent)
ai_decision_response.json → decision.confidence / warnings
    ↓ (dashboard)
🌐 全球風險雷達 card + AI 決策建議
```

---

## Dashboard 顯示建議

AI 建議區塊不應只顯示一段文字，而應至少顯示：
- 建議摘要
- 建議時間
- stale / fresh 狀態
- confidence / uncertainty
- risk note
- input refs / context version
- fallback source（AI / rule engine / stale AI）

---

## 與現有規則型引擎的關係

現有 `run_auto_decision_scan.py` 不應立刻刪除。

建議定位：
- 現階段 = fallback rule engine
- AI Decision Bridge = 更高層的實質建議層

也就是：
1. AI 有 fresh response → 顯示 AI 建議
2. AI 無 response / stale → fallback 到規則型 preview engine
3. 永遠保留 source label，避免混淆

---

## 落地建議（分階段）

### Phase 1
- 定義 request / response state contract
- dashboard 顯示 response / stale / source label
- 不直接 call AI

### Phase 2
- agent 消費 request 並寫 response
- 補 freshness / fallback / error handling

### Phase 3
- 接 outcome / reflection / review pipeline
- 與 decision quality 串接

### Phase 4
- 在風控與交易真相鏈成熟後，再評估受控自主下單

---

## 一句話總結

AI Decision Bridge 的真正目標不是做一個會說話的預演框，而是：

> 建立一套可感知、可建議、可留存、可複盤、可進化，並最終能走向受控自主決策的正式中樞接口。
