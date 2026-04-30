---
name: etf-tw-intraday-smart-scan
description: ETF_TW 盤中智慧掃描 cron 流程 — 合併盤勢掃描、重大事件偵測、外部事件情境更新、決策引擎刷新。對應決策鏈「感知→判讀」的盤中即時環節。
version: 1.0.0
created: 2026-04-20
tags: [etf-tw, cron, intraday, scan, decision-engine]
---

# ETF_TW 盤中智慧掃描 Cron 流程

盤中感知 + 判讀 + 決策引擎刷新的標準化步驟。對應決策鏈「感知 → 判讀（盤中即時）」。

## 執行步驟

### 1. 資料同步與情境更新

依序執行（順序重要，後面的腳本依賴前面的產出）：

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW

# Step 1a: 市場快取同步
.venv/bin/python scripts/sync_market_cache.py

# Step 1b: 盤中 tape context
.venv/bin/python scripts/generate_intraday_tape_context.py

# Step 1c: ETF_TW 內建盤中量化診斷
AGENT_ID=etf_master .venv/bin/python scripts/run_intraday_quant_diagnosis.py

# Step 1d: Wiki 知識沉澱
python3 scripts/distill_to_wiki.py

# Step 1e: 市場事件情境
.venv/bin/python scripts/generate_market_event_context.py

# Step 1f: 台灣市場情境
.venv/bin/python scripts/generate_taiwan_market_context.py
```

**⚠️ Pitfall #1（yfinance .TW/.TWO 後綴問題）**: `sync_market_cache.py` 對部分 ETF 會報 HTTP 404 "possibly delisted"。已確認受影響標的：00679B、00928。這是 yfinance 的 `.TW` vs `.TWO` 問題。腳本內部有 fallback 到 `.TWO`，日誌中出現可忽略，不影響功能。

**⚠️ Pitfall #2（stock-analysis-tw 已非盤中依賴）**: `stock-analysis-tw/scripts/analyze_stock.py` 在目前 etf_master profile 可能不存在，且 `--portfolio active` 本來就不可用。ETF 盤中掃描不可再呼叫該外部技能路徑；量化診斷改用 ETF_TW 內建 `scripts/run_intraday_quant_diagnosis.py`，它直接讀取 `market_cache.json`、`watchlist.json`、`positions.json` 與 `intraday_tape_context.json`，輸出 `intraday_quant_diagnosis.json`。

**Cron 指令衝突處理（2026-04-30 修正）**：若 cron prompt 又出現 `uv run skills/stock-analysis-tw/scripts/analyze_stock.py ...`，應視為舊版殘留並改成 `AGENT_ID=etf_master .venv/bin/python scripts/run_intraday_quant_diagnosis.py`。不要讓缺失外部技能成為報告缺口。

**macOS cron 注意（2026-04-29 實測）**：macOS 預設沒有 GNU `timeout` 指令；不要在 cron shell 中直接用 `timeout 180 ...`。若需要限時執行 optional stock-analysis，改用 `python3 -c` / 小型 Python wrapper 的 `subprocess.run(..., timeout=180)`，或直接跳過該 optional step。

**⚠️ Pitfall #3（security scan 管線禁令）**: 禁止 `cat file | python3 -c "..."` 管線，Hermes security scanner 會以 [HIGH] Pipe to interpreter 攔截。改用 `read_file` 工具讀 JSON，或 `terminal` 中單獨 `python3 -c "import json; ..."` 讀取。

### 2. 重大事件偵測

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python scripts/check_major_event_trigger.py
```

結果寫入 `instances/etf_master/state/major_event_flag.json`。正常輸出 `MAJOR_EVENT_TRIGGER_OK`。

### 3. 決策引擎刷新

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python scripts/refresh_decision_engine_state.py
```

此腳本是一次性完整刷新管線，內部依序執行：
- sync_strategy_link → sync_live_state → sync_orders_open_state → sync_market_cache → sync_layered_review_status → generate_market_event_context → generate_taiwan_market_context → check_major_event_trigger → sync_portfolio_snapshot → check_trading_thresholds → sync_ohlcv_history → generate_intraday_tape_context → sync_agent_summary
- 然後執行 AI Decision Bridge + dual consensus
- **然後執行 generate_ai_agent_response.py**（寫入 ai_decision_response.json，含正確的 risk_context_summary + worldmonitor 信號）
- 最後 update_decision_outcomes → build_regime_bucket_stats → update_context_weights → decision_quality

**⚠️ Pitfall #5（risk_context_summary 假接線）**: 若 `generate_ai_agent_response.py` 未在管線中，`ai_decision_response.json` 的 reasoning 三欄位會是空字串（舊版 `generate_ai_decision_response.py` 不填 reasoning）。worldmonitor 信號進了 request 卻進不了 AI 推理輸出。已於 commit c48d7ad 修復：將 `generate_ai_agent_response.py` 加入 SCRIPTS 清單。

正常輸出以 `DECISION_ENGINE_REFRESH_OK` 結尾。

**⚠️ Pitfall #4（DEDUP_SKIP）**: 若同一天已有過相同標的/方向/模式的候選單，會輸出 `DEDUP_SKIP: YYYY-MM-DD|SYMBOL|action-preview`，這是正常去重行為。

**⚠️ Pitfall #6（sync_live_state Solace 超時）**: `refresh_decision_engine_state.py` 內部會重新執行 `sync_live_state.py`，若永豐券 Solace 連線超時（`Connect attempt timed out` / `connected failed, return Not ready`），該步驟會失敗，整體結果為 `REFRESH_PARTIAL_OK`。其餘步驟不受影響，持倉數據可能非即時（仍可使用上一次成功同步的快取）。此為間歇性網路問題，非腳本錯誤。

**⚠️ Pitfall #7（provenance append NoneType.get 警告）**: `run_auto_decision_scan.py` 在共識計算後 append provenance record 時，偶發 `[provenance] Failed to append provenance record: 'NoneType' object has no attribute 'get'` 警告。這是 provenance 記錄物件為 None 時的防禦性警告，不影響決策結果（候選單、共識層級仍正常產出）。可安全忽略，但應在產出報告的「已知問題」中標註。

### 4. 讀取 state 產出報告

**Cron 實作建議（2026-04-28 實測）**：在 cron session 內建議用 `execute_code` 一次完成「跑腳本 → 讀 JSON → 生成報告素材」，比多次 `terminal()` 更穩。路徑用 `os.path.expanduser('~')` 解析為實際 `/Users/...` home；讀 JSON 用 Python `json.load(open(path, encoding='utf-8'))`，避免 `read_file()` 行號格式與 shell pipeline security scanner 問題。

用 `read_file` 工具依序讀取以下關鍵 state 檔案：

**必讀：**
- `instances/etf_master/state/intraday_tape_context.json` — 盤中 tape 信號（實務 schema 以 `watchlist_signals` 為主；欄位包含 `current_price`, `daily_return_pct`, `intraday_return_pct`, `range_pos_pct`, `relative_strength`, `tape_label`）
- `instances/etf_master/state/market_event_context.json` — 事件層數據
- `instances/etf_master/state/market_context_taiwan.json` — 市場體制量化數據
- `instances/etf_master/state/major_event_flag.json` — 重大事件觸發狀態
- `instances/etf_master/state/auto_preview_candidate.json` — 決策引擎候選單
- `instances/etf_master/state/positions.json` — 即時持倉（⚠️ 注意：主鍵是 `"positions"` 陣列，不是 `"holdings"`；每筆含 `symbol`, `quantity`, `average_price`, `current_price`, `market_value`, `unrealized_pnl`）
- `instances/etf_master/state/portfolio_snapshot.json` — ⚠️ **現金與總資產必讀**：`positions.json` 可能不含現金（cash=0），现金餘額和總資產需從此檔的 `cash` 和 `total_equity` 欄位讀取
- `instances/etf_master/state/agent_summary.json` — 策略摘要抬頭（`strategy_header` 欄位格式：`[目前投資策略:XXX, 情境覆蓋:YYY]`）
- `instances/etf_master/state/decision_quality.json` — 決策品質摘要（可選，但報告中可用來補充 7 日決策品質）
- `instances/etf_master/state/regime_bucket_stats.json` / `context_weights.json` — 決策引擎刷新後的 regime bucket 與權重（可選，用於除錯）
- `instances/etf_master/state/ai_decision_response.json` — AI Bridge 候選與 reasoning（可選，用於 cross-check 規則引擎候選衝突）

### 4b. Wiki 判讀層更新（必要）

掃描完成後應同步更新：
- `instances/etf_master/wiki/market-view.md`
- `instances/etf_master/wiki/risk-signal.md`

更新原則：
1. 從 `market_context_taiwan.json` 讀 `market_regime`、`risk_temperature`、`income_tilt`、`defensive_tilt`、`core_tilt`、`context_summary`、`quant_indicators`。
2. 從 `market_event_context.json` 讀 `event_regime`、`global_risk_level`、`geo_political_risk`、`rate_risk`、`energy_risk`、`taiwan_equity_impact`、`active_events`。
3. 從 `major_event_flag.json` 讀 `triggered/reason/level`。
4. 先讀舊 `market-view.md` 中的上一版「市場體制 / 風險溫度」，若本次不同，在報告和 wiki 歷史中加粗標記：`體制/風險訊號變動：old_regime / old_risk → new_regime / new_risk`。
5. 不要只跑 `distill_to_wiki.py` 就以為判讀層已更新；`distill_to_wiki.py` 更新的是 ETF 個別 wiki 頁，`market-view.md` / `risk-signal.md` 仍需另外寫入。


### 5. 報告格式

```
[目前投資策略:XXX, 情境覆蓋:YYY]

# ETF_TW 盤中智慧掃描報告 — YYYY-MM-DD HH:MM

## 📊 持倉概覽
表格：標的/數量/均價/現價/市值/未實現損益/報酬率

## 🌐 市場情境判讀
- 市場體制、風險溫度、盤勢氛圍
- 量化指標（RSI 分佈、MACD、均線、波動）
- 關注風險事件

## 🔍 盤中個股 tape 信號
表格：標的/現價/日報酬/盤中報酬/Range%/相對強弱/標籤

## ⚠️ 重大事件偵測
觸發狀態摘要

## 🎯 決策引擎結果
- 共識層級（Tier 1/2/3）
- 候選單明細
- 重要：候選單不會自動下單

## 📝 執行摘要
步驟狀態表 + 已知問題
```

## 注意事項

- 這是 cron 自動執行，無法互動。遇缺數據時標註「⚠️ 數據缺失」而非追問
- 報告以繁體中文輸出
- 策略抬頭從 `agent_summary.json` 的 `strategy_header` 欄位讀取，必須在回覆最前面顯示
- `distill_to_wiki.py` 使用系統 `python3`（非 .venv），其餘腳本使用 `.venv/bin/python`
- 00679B 在 Yahoo Finance (.TW suffix) 會 404；market_cache 腳本已有 .TWO fallback 但仍會噴 HTTP 404 log，可忽略
- `run_intraday_quant_diagnosis.py` 是 ETF_TW 內建量化診斷入口；不要依賴已吸收的 `stock-analysis-tw` 外部技能路徑
