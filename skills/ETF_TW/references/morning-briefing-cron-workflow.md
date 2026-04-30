---
name: etf-tw-morning-briefing
description: ETF_TW 早班準備 cron 流程 — 盤前資料同步、早期復盤、體制判讀、風險訊號更新、wiki 寫入、早班報告產出
version: 1.0.0
created: 2026-04-20
tags: [etf-tw, cron, morning, briefing, wiki]
---

# ETF_TW 早班準備 Cron 流程

盤前感知 + 復盤的標準化步驟。對應決策鏈「感知 → 判讀」。

## 執行步驟

### 1. 資料同步（感知）

依序執行，AGENT_ID=etf_master：

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python scripts/sync_market_cache.py
.venv/bin/python scripts/sync_portfolio_snapshot.py
.venv/bin/python scripts/sync_orders_open_state.py
.venv/bin/python scripts/generate_watchlist_summary.py --mode am
AGENT_ID=etf_master .venv/bin/python scripts/generate_market_event_context.py
AGENT_ID=etf_master .venv/bin/python scripts/generate_taiwan_market_context.py
```

**⚠️ Pitfall #0**: 使用者或舊 cron 指令可能只列出 `sync_market_cache.py`、portfolio、orders、watchlist，沒有列出 `generate_market_event_context.py` / `generate_taiwan_market_context.py`。但早班報告要更新 `market-view.md` / `risk-signal.md` 時，必須先刷新這兩個 context；否則會拿昨日 `market_context_taiwan.json` / `market_event_context.json` 寫入今日 wiki，造成「資料同步成功但體制判讀 stale」。做法：watchlist 後補跑 event context → Taiwan context，再重新讀 state 後才 patch wiki。

**⚠️ Pitfall #1**: `generate_watchlist_summary.py` 必須帶 `--mode am` 或 `--mode pm`，否則報錯 exit code 2。

**⚠️ Pitfall #2**: `sync_market_cache.py` 對 00679B.TW 會報 "possibly delisted"。這是 yfinance 的 .TW 與 .TWO 問題，腳本內部已有 fallback 到 .TWO，不影響功能。日誌中出現可忽略。

**⚠️ Pitfall #2b**: `sync_market_cache.py` 對多檔 .TWO 標的（0056, 006208, 00713, 00830, 00929, 00935 等）會報 "possibly delisted; no price data found"。這是 yfinance 週末/清晨資料暫時不可得的已知現象，腳本會 fallback 到 last_known_cache。若初次執行超時（exit 124），重新執行通常會成功（exit 0 + MARKET_CACHE_SYNC_OK），因後續請求會命中快取。建議 timeout 設 300s。

**⚠️ Pitfall #3**: `patch` 工具 replace 模式更新 wiki markdown 表格時，`old_string` 和 `new_string` 中的表格行必須精確匹配原始格式（單 `|`），不要因複製貼上而產生 `||` 雙線格式。patch 前務必對照 read_file 的原始內容。

### 2. 早期復盤

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python scripts/layered_review_cron_registry_live.py
```

正常執行無 stdout 輸出是預期行為（不代表失敗）。檢查 exit code = 0 即可。

### 3. 讀取同步數據

用 `read_file` 工具讀取以下 state 檔案（**不要用 `cat | python3 -m json.tool`**，會觸發 security scan 阻擋）：

**必讀：**
- `instances/etf_master/state/portfolio_snapshot.json` — 持倉摘要
- `instances/etf_master/state/positions.json` — 持倉明細
- `instances/etf_master/state/account_snapshot.json` — 帳戶摘要
- `instances/etf_master/state/orders_open.json` — 活躍掛單
- `instances/etf_master/state/market_context_taiwan.json` — 市場體制量化數據
- `instances/etf_master/state/market_event_context.json` — 事件層風險數據
- `instances/etf_master/state/major_event_flag.json` — 重大事件觸發
- `instances/etf_master/state/worldmonitor_snapshot.json` — 全球風險/咽喉點
- `instances/etf_master/state/strategy_link.json` — 當前策略

**選讀：**
- `instances/etf_master/state/market_cache.json` — 個別報價（計算日漲跌幅用）
- `instances/etf_master/state/daily_pnl.json` — 每日損益
- `instances/etf_master/state/layered_review_status.json` — 復盤狀態

**⚠️ Pitfall #3**: 禁止 `cat file | python3` 管線，Hermes security scanner 會以 [HIGH] Pipe to interpreter 攔截。改用 `read_file` 直接讀 JSON，或 `terminal` 中單獨 `python3 -c "import json; ..."` 讀取。

**⚠️ Pitfall #4**: 帳戶摘要的總資產應優先採用 `portfolio_snapshot.json.total_equity`。`account_snapshot.json.total_equity` 在 live broker 同步後可能只等於現金餘額（未納入持倉市值），不可直接當作總資產；`account_snapshot.json` 主要用於 cash、settlements、settlement_safe_cash。若兩者衝突，報告中明確註記採用來源。

**⚠️ Pitfall #5**: 產出「上次 vs 本次」比較前，必須先讀取尚未 patch 的 `~/wiki/concepts/market-view.md` 與 `~/wiki/concepts/risk-signal.md`，把舊體制、舊風險溫度、舊 SMA20/RSI/MACD 描述當作上次值；完成 wiki patch 後再讀取驗證。不要在 patch 後才回推上次狀態。

**⚠️ Pitfall #6**: `market_context_taiwan.quant_indicators.sma_structure` 與 `market_event_context.breadth` 可能使用不同統計口徑，出現如 `above_sma20_pct=20.0` 但 breadth 顯示 `above_sma20_count=1/18` 的差異。報告時應明確標示資料來源與口徑（量化層結構 vs 事件廣度），不要混成單一百分比。

### 4. 體制判讀與 Wiki 更新

#### 4a. 判讀邏輯

從 `market_context_taiwan.json` 提取：
- `market_regime` — 體制狀態
- `risk_temperature` — 風險溫度
- `quant_indicators.rsi_distribution` — RSI 分佈（超買/超賣佔比）
- `quant_indicators.macd_breadth` — MACD 多空佔比
- `quant_indicators.sma_structure` — 均線結構（站上/跌破 SMA20）
- `quant_indicators.group_trends` — 分組趨勢（core/income/defensive/growth）
- `quant_indicators.volatility` — 波動率

從 `market_event_context.json` 提取：
- `event_regime` / `global_risk_level` / `geo_political_risk` / `energy_risk`

從 `worldmonitor_snapshot.json` 提取：
- `supply_chain.global_stress_level`
- 個別咽喉點 status/disruptionScore（尤其 hormuz_strait, bab_el_mandeb, taiwan_strait）

#### 4b. Wiki 更新

**市場體制頁** `~/wiki/concepts/market-view.md`：
- 更新 `updated` 日期（frontmatter）
- 更新「當前體制判定」表格（體制、風險溫度、各偏重、更新時間）
- 更新「體制判讀說明」段落（量化層 vs 事件層的變化描述）
- 更新「當前驅動因子」列舉（按重要度排列，附偏多/偏空標記）
- 更新「今日轉換評估」

**風險訊號頁** `~/wiki/concepts/risk-signal.md`：
- 更新 `updated` 日期（frontmatter）
- 更新「核心訊號」表格更新時間
- 更新「今日判讀」段落
- 更新「活躍風險事件」列舉
- 在「訊號變動歷史」表格加入今日紀錄
- 更新「當前行動對照」段落（持倉數據用 portfolio_snapshot 同步後的最新值）

**使用 `patch` 工具的 replace 模式**進行精確更新，不要用 write_file 覆蓋整份文件。

### 5. 早班報告產出

報告格式（繁體中文）：

```
[目前投資策略:XXX, 情境覆蓋:YYY]

# 📊 YYYY-MM-DD 早班報告

## 一、持倉與帳戶
- 現金餘額、總資產、各部位比重（表格）
- 持倉明細表格（標的/股數/均價/現價/市值/損益/報酬率）
- 較上次變化摘要

## 二、市場體制判讀
- 體制結論
- 關鍵指標變化比較表（上次 vs 本次）
- 核心判讀（✅ 改善 / ⚠️ 注意 / 🔴 風險）

## 三、風險訊號更新
- 核心訊號表格（含較上次變化）
- 活躍風險事件（🆕 新增 / 🔄 持續）
- 訊號變動歷史已更新確認

## 四、今日觀察重點
- 3 個觀察點（表格：觀察重點/對應決策鏈步驟/觸發行動）
- 決策鏈總結
```

**策略抬頭**：從 `strategy_link.json` 讀取 `base_strategy` 和 `scenario_overlay`，必須在回覆最前面顯示。

## 注意事項

- 這是 cron 自動執行，無法互動。遇缺數據時標註「⚠️ 數據缺失」而非追問
- 報告以繁體中文輸出
- 數據計算日漲跌幅時，用 `market_cache.json` 的 `current_price` vs `prev_close`
- Wiki 更新後，AI Decision Bridge 下次執行時會自動注入最新 wiki context