---
name: etf-tw-post-market-review
description: ETF_TW 盤後收工 cron 流程 — 合併盤後摘要、每日復盤、決策品質評分。決策鏈進入「判讀 → 預判」階段。
version: 1.0.0
created: 2026-04-20
tags: [etf-tw, cron, post-market, review, decision-quality, wiki]
---

# ETF_TW 盤後收工 Cron 流程

盤後資料同步 + 深度診斷 + Wiki 沉澱 + 決策品質評分 + 預判，合併原「盤後摘要 + 每日復盤 + 決策品質評分」。

決策鏈位置：感知 → **判讀 → 預判**

## 執行步驟

### 1. 盤後資料同步

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python scripts/sync_market_cache.py
.venv/bin/python scripts/sync_portfolio_snapshot.py
.venv/bin/python scripts/generate_watchlist_summary.py --mode pm
```

**⚠️ Pitfall #1**: `sync_positions.py` 已不存在 — 功能已併入 `sync_portfolio_snapshot.py`。不要嘗試執行。

**⚠️ Pitfall #2**: `generate_watchlist_summary.py` 必須帶 `--mode pm`（盤後模式），不帶會 exit code 2。

### 2. 全維度量化診斷

**必須動態讀取** `positions.json` 的 `positions` 陣列（鍵名是 `positions`，不是頂層），提取所有 `symbol` 欄位，轉換為 yfinance ticker 格式後傳給 analyze_stock。不要硬編碼 ticker 列表——持倉會變動。

```python
# positions.json 結構：{"positions": [{"symbol": "00679B", ...}, ...], "updated_at": ...}
# 轉換規則：00679B → 00679B.TWO（櫃買），其餘 → .TW（上市）
# 剔除 00928.TW（會導致 analyze_stock 報錯中斷整批）
```

```bash
cd ~/.hermes/profiles/etf_master
uv run skills/stock-analysis-tw/scripts/analyze_stock.py --fast \
  --state-dir skills/ETF_TW/instances/etf_master/state/ \
  0056.TW 006208.TW 00679B.TWO 00878.TW 00919.TW 00922.TW 00923.TW 00939.TW
```

**⚠️ Pitfall #3**: `--portfolio active` 參數不存在（會報 "Portfolio 'active' not found"）。必須從 positions.json 讀取 ticker 列表，逐一作為 positional argument 傳入。

**⚠️ Pitfall #4**: ETF 在 yfinance 無 fundamentals（quoteSummary 404），這是正常現象。輸出仍會有技術面/動能/市場情緒分析，但 confidence 偏低。日誌中 "No fundamentals data found" 和 "No earnings dates found" 可忽略。

**⚠️ Pitfall #5**: 00679B 的 yfinance 代碼是 `.TWO` 不是 `.TW`。用錯會導致找不到資料。其他 ETF 多數用 `.TW`。

**⚠️ Pitfall #5b**: `00928.TW` 會導致 `analyze_stock.py` 報 `Error: Invalid ticker '00928.TW' or data unavailable` 並 exit code 2，整批分析中斷。解法：從 positional args 中剔除 00928.TW，連同其他 .TWO 標的一併排除後重跑。建議在拼湊 ticker 列表時，先過濾掉已知會失敗的標的。

**⚠️ Pitfall #5c**: 在 Hermes profile 的傘狀整理後，`skills/stock-analysis-tw/scripts/analyze_stock.py` 可能不存在（僅留下 `taiwan-finance/references/stock-analysis-tw.md` 文件）。盤後 cron 不可因此中斷；應先用 `search_files(target="files", pattern="analyze_stock.py", path="~/.hermes")` 或 Python `Path.exists()` 驗證腳本存在。若不存在，改用 yfinance fallback 自行計算持倉技術診斷（收盤、日漲跌、RSI14、MA20、布林位置、MACD、20日動能、成交量），並在系統狀態表標記 `stock-analysis-tw analyze_stock.py：路徑不存在，已用 yfinance fallback`。

### 3. Wiki 知識沉澱

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
python3 scripts/distill_to_wiki.py
```

正常輸出類似：`完成：更新 11 個 wiki 頁面，跳過 7 個`

### 4. 收盤專業線圖

```bash
cd ~/.hermes/profiles/etf_master
uv run skills/stock-market-pro-tw/scripts/yf.py report 0050.TW 3mo
```

產出 PNG 至 `/tmp/0050.TW_pro.png`，同時輸出文字摘要含 RSI/MACD/BB 等關鍵指標。

### 5. 讀取 State 數據（決策品質評分用）

用 `read_file` 或 `terminal` 讀取以下檔案：

**必讀：**
- `instances/etf_master/state/portfolio_snapshot.json` — 持倉摘要（含市值、未實現PnL）
- `instances/etf_master/state/positions.json` — 持倉明細
- `instances/etf_master/state/account_snapshot.json` — 帳戶摘要
- `instances/etf_master/state/orders_open.json` — 活躍掛單
- `instances/etf_master/state/strategy_link.json` — 當前策略
- `instances/etf_master/state/market_event_context.json` — 事件層風險
- `instances/etf_master/state/intraday_tape_context.json` — Tape 盤勢信號（含 18 檔 watchlist 的強弱分類）
- `instances/etf_master/state/decision_quality_report.json` — 決策品質報告
- `instances/etf_master/state/agent_summary.json` — Agent 摘要（含策略抬頭）

**選讀：**
- `instances/etf_master/state/daily_pnl.json` — 每日損益
- `instances/etf_master/state/macro_indicators.json` — VIX/台幣等宏觀指標
- `instances/etf_master/state/market_context_taiwan.json` — 台灣市場體制量化
- `instances/etf_master/state/worldmonitor_snapshot.json` — 全球風險
- `instances/etf_master/state/major_event_flag.json` — 重大事件旗標

**⚠️ Pitfall #6**: `taiwan_market_context.json` 不存在，正確檔名是 `market_context_taiwan.json`（注意順序反轉）。

**⚠️ Pitfall #7**: `market_cache.json` 結構可能不符預期（非 dict-of-dict），嘗試 `.get("close")` 會報 AttributeError。需先確認結構或改用其他數據源取報價。

**⚠️ Pitfall #8**: 禁止 `cat file | python3` 管線，Hermes security scanner 會攔截。改用 `read_file` 或 `terminal` 中單獨 `python3 -c` 讀取。

**⚠️ Pitfall #9**: `account_snapshot.json` 的 `total_equity` 可能只反映 cash 金額（不包含 market_value），與 `portfolio_snapshot.json` 的 `total_equity` 不一致。報告中的總資產數字應以 `portfolio_snapshot.json` 為準。

**⚠️ Pitfall #10**: 部分 cron 排程的 model（如 glm-5.1:cloud via ollama-cloud）不支援 vision_analyze，呼叫會報 400 錯誤。盤後報告中線圖分析僅依賴 `yf.py report` 的文字輸出即可（RSI/MACD/BB 數值都在 stdout），不需強制截圖分析。

**⚠️ Pitfall #10b**: `skills/stock-market-pro-tw/scripts/yf.py` 也可能在 Hermes profile 中不存在。若 `uv run .../yf.py report 0050.TW 3mo` 報 `No such file or directory`，不要停在錯誤；改用 yfinance fallback 產生 0050 技術摘要（至少包含收盤、日漲跌、RSI14、MA20、布林位置、MACD/Signal、20日動能、成交量），並明確標記「專業線圖腳本不存在，已用 yfinance fallback；未產生 PNG」。

**⚠️ Pitfall #11**: `daily_pnl.json` 可能嚴重過期（曾觀察到資料停留在 4 天前），與實際交易日不匹配。使用前應檢查 `date` 欄位是否為今日，若過期則標註「⚠️ 數據缺失」。

**⚠️ Pitfall #12b**: `macro_indicators.json` 同樣可能嚴重過期（曾觀察到資料停留在 11+ 天前），其 `vix_proxy` 值可能與 yfinance 即時 VIX 嚴重不一致（例：proxy 14.4 vs 實際 19.3）。使用前應檢查 `updated_at`，若過期則以 `analyze_stock.py` 或 `yf.py report` 的即時 VIX 為準，並標註「⚠️ 宏觀指標過期」。

**⚠️ Pitfall #13**: `orders_open.json` 可能殘留前一交易日或更早的 pending / verified=false 掛單（stale order），即使來源是 `live_broker` 也不應直接視為今日有效委託。盤後報告需列出其 `observed_at`、`verified`、`broker_order_id`、`broker_status`，並在「明日操作傾向」中要求開盤前用 live broker 查單重新核對；若 broker 端不存在，應建議清理 stale state，避免重複下單或誤判可用現金。

### 6. 決策品質評分

從 `decision_quality_report.json` 提取：
- `total_decisions` / `total_pending` — 決策積累 vs 待驗
- `strategy_alignment_rate` — 策略一致性
- `chain_breakdown` — rule_engine / ai_bridge / tier1 的勝率
- `interception_rate` — 風控攔截率

評分等級：
- **A**: 勝率 >60%、一致性 >80%、無風控攔截
- **B**: 勝率 >50%、一致性 >60%
- **C**: 建設期（樣本不足或 pending 過多）
- **D**: 勝率 <40% 或攔截率 >20%
- **F**: 多項指標異常

### 7. 盤後報告產出

報告結構（繁體中文）：

```
[目前投資策略:XXX, 情境覆蓋:YYY]

# ETF_TW 盤後收工報告｜YYYY-MM-DD (星期)

## 一、帳戶總覽
  總資產 / 持倉市值 / 現金 / 現金比 / 未實現PnL / 持倉數 / 模式 / 掛單

## 二、持倉明細與盤後診斷
  表格：標的/持有/均價/收盤/市值/PnL/日漲跌/診斷
  持倉結構分析（核心/收益/防守 佔比）

## 三、市場環境判讀
  大盤氛圍 / 事件體制 / VIX / 寬度 / 關注事件 / Tape 速寫

## 四、0050 技術線圖摘要
  RSI / BB / MACD / 日漲跌 / 趨勢

## 五、決策品質評分
  決策鏈狀態表格 / 總評等級

## 六、判讀 → 預判：明日展望
  判讀（今日收斂事實 3-5 點）
  預判（情境表：情境/機率/觸發/影響）
  明日操作傾向

## 七、今日系統狀態
  各腳本執行結果 checklist
```

**策略抬頭**：從 `strategy_link.json` 讀取 `base_strategy` 和 `scenario_overlay`，必須在回覆最前面顯示。

### 8. 持倉結構分析計算

從 `portfolio_snapshot.json` 的 `holdings` 陣列，按 `intraday_tape_context.json` 的 `group` 欄位分類。**group 欄位是動態的**，不要硬編碼標的對群組的映射——持倉會變動，watchlist 也會擴充。

分類邏輯：
1. 讀取 `intraday_tape_context.json` 的 `watchlist_signals` 陣列
2. 建立 `symbol → group` 對照表
3. 對 `portfolio_snapshot.json` 的每筆 holding，查表取得 group
4. 計算各群佔持倉市值百分比，標記結構偏移

常見群組（僅供參考，以 tape context 實際值為準）：
- **核心區** (core): 0050, 006208, 00922, 00923
- **收益區** (income): 00878, 00919, 0056, 00929, 00940, 00713
- **防守區** (defensive): 00679B, 00687B, 00720B, 00694B
- **成長區** (growth): 00830, 00892, 00935

**⚠️ Pitfall #12a**: 不在 tape context 中的 holding（如 00928、00939）會落入「其他」分群。報告中應標註為未分類並建議清理或新增至 watchlist。

### 9. 全球風險雷達整合

從 `worldmonitor_snapshot.json` 提取關鍵要塞狀態，整合至「市場環境判讀」：

- `supply_chain.global_stress_level` — 全球供應鏈壓力等級（low/medium/high/critical）
- `supply_chain.chokepoints` — 各要塞干擾分數與戰爭風險等級
- 報告中以表格呈現 status≠green 或 disruptionScore>0 的要塞

**納入預判邏輯**：供應鏈 HIGH 時，預判情境應拉高「急跌」機率、加重「防守補位」建議權重。

## 注意事項

- 這是 cron 自動執行，無法互動。遇缺數據時標註「⚠️ 數據缺失」而非追問
- 報告以繁體中文輸出
- 週末/國定假日無交易數據時，仍執行同步（會拿到前一日收盤價），報告標註「非交易日」
- `analyze_stock` 對 ETF 的 confidence 偏低是正常 — ETF 無 earnings/fundamentals，不影響技術面判讀
- 決策品質在冷啟動期（total_decisions < 10）評分一定是 C，不需要驚訝