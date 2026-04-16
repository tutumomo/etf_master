# ETF_TW 真相層級治理 (Truth Level Governance) v1.1

## 核心原則：真相分級制度

ETF_TW 不再採用「唯一真相源 (SSoT)」的單一思維，而是根據資訊的即時性與確定性，將所有狀態區分為以下三個層級：

### 1. Level 1: Live Direct Evidence (第一級：即時直接證據)
- **定義**：直接從券商 API (如 Shioaji `list_positions`, `list_trades`) 獲取且已標註為「已成交 (Filled)」或「已掛單 (Open)」的即時原始數據。
- **權威性**：最高。任何與此不符的本機資訊皆視為過時或錯誤。

### 2. Level 2: Live Unconfirmed (第二級：即時待驗證)
- **定義**：執行送單指令 (`place_order`) 後得到的 API 初始回傳成功，但尚未透過 Level 1 查詢機制確認其在交易所落地。
- **權威性**：中等。視為「意圖已送達」，但必須標註 `[驗證中]` 並提示使用者以隨後的 Level 1 查詢為準。

### 3. Level 3: Secondary Info / Snapshots (第三級：次級資訊與快照)
- **定義**：存放在本機 `instances/<agent_id>/state/` 目錄下的 JSON 檔案、Dashboard 衍生顯示、以及 Agent 記憶中的歷史摘要。
- **權威性**：最低。僅視為「本機狀態快照 (Snapshot)」，主要用於減少 API 呼叫、提供 UI 渲染與歷史追蹤。在進行交易決策前，必須同步 (Sync) 至 Level 1。

## 狀態存儲規範

### 1. Instance state 目錄
所有本機狀態快照檔，統一寫入：
```text
ETF_TW/instances/<agent_id>/state/
```
Hermes 版範例：
```text
~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/
```

### 2. Root state 僅視為 legacy / migration residue
`ETF_TW/state/` 不再視為正式運作資訊來源。

### 3. Agent 與 ETF_TW 必須讀同一份 instance state
- dashboard 必須讀 instance state
- sync scripts 必須寫 instance state
- agent 回覆 current state 時，必須優先讀 instance state 對應檔案

### 4. 下游摘要不可反寫上游資訊
- `agent_summary.json`、`intraday_tape_context.json` 屬展示 / 摘要層。
- 不得覆寫 `positions.json`、`account_snapshot.json`、`orders_open.json` 等基礎快照。

## 正式 Refresh Pipeline
1. `sync_strategy_link.py`
2. `sync_live_state.py / sync_paper_state.py`
3. `sync_market_cache.py`
4. `generate_market_event_context.py`
5. `generate_taiwan_market_context.py`
6. `check_major_event_trigger.py`
7. `sync_portfolio_snapshot.py`
8. `sync_ohlcv_history.py`
9. `generate_intraday_tape_context.py`
10. `sync_agent_summary.py`

## 策略抬頭對齊
唯一抬頭來源：`instances/<agent_id>/state/strategy_link.json`
