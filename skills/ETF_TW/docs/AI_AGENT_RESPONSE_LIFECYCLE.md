# AI Agent Response Lifecycle

## 目的

這份文件定義 AI Decision Bridge 從 placeholder response engine 過渡到 agent-consumed response 的最小生命週期。

目標不是立刻把所有邏輯切到 AI agent，而是先固定好：
- response contract
- source 標記
- review 欄位
- 後續 outcome / reflection 可接的位置

---

## Source 分層

### `source = "ai_decision_bridge"`
- 代表目前由 bridge 腳本產生的 placeholder / minimal response
- 用途：打通 pipeline、驗證 request → response → dashboard 顯示

### `source = "ai_agent"`
- 代表已由 AI agent 真正消費 request 後產生的 response
- 用途：作為未來正式智能建議 artifact

---

## Agent-Consumed Response 最小欄位

```json
{
  "request_id": "string",
  "generated_at": "ISO timestamp",
  "expires_at": "ISO timestamp",
  "stale": false,
  "source": "ai_agent",
  "agent": {
    "name": "ETF_Master",
    "version": "agent-consumed-phase0"
  },
  "decision": {
    "summary": "string",
    "action": "watch_only|preview_buy|preview_sell|hold",
    "confidence": "low|medium|high",
    "uncertainty": "string",
    "strategy_alignment": "string"
  },
  "candidate": {},
  "reasoning": {
    "market_context_summary": "string",
    "position_context_summary": "string",
    "risk_context_summary": "string"
  },
  "warnings": [],
  "input_refs": {},
  "review": {
    "status": "pending|reviewed|superseded",
    "reviewed_at": null,
    "human_feedback": null
  }
}
```

---

## 最小生命週期

### Stage A：Bridge Placeholder
- request 由 state builder 產生
- response 由 placeholder bridge script 產生
- `source = ai_decision_bridge`

### Stage B：Agent Consumed
- AI agent 讀取 request
- AI agent 產生 response artifact
- `source = ai_agent`
- 補 `review` 欄位

### Stage C：Review / Outcome
- 人工或後續腳本補 review
- 可標記 `review.status = reviewed`
- 可連接 outcome / reflection pipeline

---

## 轉換原則

1. 不直接刪除 placeholder response engine
2. agent response 與 placeholder response 應能共存一段時間
3. dashboard 顯示必須明確標示 source，避免混淆
4. review 欄位是未來 decision quality / reflection 的接點，不可省略

---

## 一句話總結

在真正把 AI agent 接進主線前，先固定 agent-consumed response 的 contract，讓系統從今天開始就具備：
- 可辨識來源
- 可保留 review 狀態
- 可朝 outcome / reflection / 受控自治延伸
