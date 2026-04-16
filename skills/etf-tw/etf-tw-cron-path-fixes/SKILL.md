---
name: etf-tw-cron-path-fixes
description: ETF_TW 在 Hermes cron 環境中的腳本替代與路徑修正備忘
---

# ETF_TW cron 路徑修正

## Trigger
當你在 Hermes cron / 排程 / 盤後批次任務中執行 ETF_TW 腳本，且舊 SOP 或舊提示提到 `sync_positions.py` 時使用。

## 問題
舊流程可能寫：
```bash
.venv/bin/python scripts/sync_positions.py
```
但在目前 `~/.hermes/profiles/etf_master/skills/ETF_TW/` 環境中，**這個檔案不存在**，直接執行會報：
```text
can't open file '.../scripts/sync_positions.py': [Errno 2] No such file or directory
```

## 正確替代流程
若目的是同步 live 持倉與盤後快照，改用：
```bash
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/sync_live_state.py
.venv/bin/python scripts/sync_portfolio_snapshot.py
```

## 作用分工
- `sync_live_state.py`
  - 寫入 `instances/etf_master/state/positions.json`
  - 寫入 `instances/etf_master/state/account_snapshot.json`
- `sync_portfolio_snapshot.py`
  - 依 live broker / state 產生 `portfolio_snapshot.json`
  - 給 dashboard / 摘要 / 報告使用

## 盤後批次建議順序
```bash
.venv/bin/python scripts/sync_market_cache.py
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/sync_live_state.py
.venv/bin/python scripts/sync_portfolio_snapshot.py
.venv/bin/python scripts/generate_watchlist_summary.py --mode pm
.venv/bin/python scripts/score_decision_quality.py
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/review_auto_decisions.py --mode daily
```

## 注意事項
- `generate_watchlist_summary.py` 盤後一定要帶 `--mode pm`
- 若沒帶 `OPENCLAW_AGENT_NAME=etf_master`，部分腳本會出現 warning，雖然通常仍預設到 `etf_master`，但不建議依賴這個 fallback
- 正式送單與 state 同步仍應優先使用 `.venv/bin/python`

## 盤中智慧掃描流程（完整 pipeline）

這是盤中即時感知與判讀環節，合併原「盤勢掃描 + 重大事件偵測 + 外部事件情境更新 + 決策引擎刷新」。

### 正確順序（6 步驟）

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW

# Step 1: 資料同步
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/sync_market_cache.py
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/generate_intraday_tape_context.py

# Step 2: 量化診斷（注意：不能用 --portfolio active，要傳個股 ticker）
cd ~/.hermes/profiles/etf_master
uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW 00878.TW 00919.TW --fast --state-dir skills/ETF_TW/instances/etf_master/state/

# Step 3: distill_to_wiki.py — 檔案不存在，跳過此步驟
# python3 scripts/distill_to_wiki.py  ← 不存在，勿執行

# Step 4: 情境生成
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/generate_market_event_context.py
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/generate_taiwan_market_context.py

# Step 5: 重大事件偵測
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/check_major_event_trigger.py

# Step 6: 決策引擎刷新（會自動跑完整 refresh pipeline）
OPENCLAW_AGENT_NAME=etf_master .venv/bin/python scripts/refresh_decision_engine_state.py
```

### 已知陷阱

1. **`distill_to_wiki.py` 不存在** — 在當前版本中此檔案尚未建立，跳過即可，不要嘗試執行。

2. **`analyze_stock.py --portfolio active` 失敗** — 不認識 `active` 這個 portfolio 名稱。正確用法是直接傳 ticker 符號：
   ```bash
   uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW 00878.TW --fast --state-dir ...
   ```
   但 Yahoo Finance 對部分台灣 ETF（尤其是債券型如 00679B.TW）回傳 404，這是已知資料源限制。

3. **疑似下市 ETF** — 00687B、00694B、00720B 在 Yahoo Finance 上找不到資料（404），major_event_flag 會因此觸發 L3。這是資料源問題，不是真正的市場事件。建議從 watchlist/monitoring list 中移除這些標的。

4. **`AGENT_ID` 警告** — 不帶 `OPENCLAW_AGENT_NAME=etf_master` 時會出現 warning，雖然會 fallback 到 `etf_master`，但建議明確指定以避免跨 agent 狀態污染。

5. **Yahoo Finance 台股 ETF 限制** — Yahoo Finance 對台灣債券型 ETF（`.TW` 後綴）的報價支援不穩定，常見 404 錯誤。對於持倉中的 00679B 等標的，broker API（永豐）的即時報價是主要真相來源，Yahoo 僅作輔助。

### 決策引擎輸出關鍵檔案

掃描完成後，重點閱讀：
- `state/major_event_flag.json` — 事件觸發層級
- `state/market_event_context.json` — 事件情境與風險等級
- `state/intraday_tape_context.json` — 盤面帶狀訊號
- `state/auto_preview_candidate.json` — 預覽候選（含雙引擎共識）
- `state/decision_quality.json` — 決策品質評估
- `state/agent_summary.json` — 彙整摘要
- `state/strategy_link.json` — 策略標頭

## 驗證
至少檢查以下檔案時間有更新：
- `instances/etf_master/state/positions.json`
- `instances/etf_master/state/account_snapshot.json`
- `instances/etf_master/state/portfolio_snapshot.json`
- `instances/etf_master/state/intraday_tape_context.json`
- `instances/etf_master/state/major_event_flag.json`
- `instances/etf_master/state/market_event_context.json`
- `instances/etf_master/state/auto_preview_candidate.json`
