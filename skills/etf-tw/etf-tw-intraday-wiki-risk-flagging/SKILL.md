---
name: etf-tw-intraday-wiki-risk-flagging
description: 盤中掃描更新 wiki 時，將 major_event_flag 的資料完整性/報價異常明確寫入 risk-signal 活躍風險事件與變動歷史。
version: 1.0.0
---

# ETF_TW 盤中 Wiki 風險旗標補強

## 何時使用
- 執行 ETF_TW 盤中智慧掃描後
- 需要更新 `instances/etf_master/wiki/market-view.md` 與 `risk-signal.md`
- 本輪有讀取 `major_event_flag.json`

## 核心規則
1. `major_event_flag.json` 若 `triggered: true`，不能只在報告裡提一次。
2. 必須同步落到 `risk-signal.md` 的兩個地方：
   - `活躍風險事件`：置頂新增一條摘要，帶入 `reason`、`level`、`category`
   - `訊號變動歷史`：新增一列記錄旗標觸發
3. 若是資料完整性或報價缺失（例如多檔 ETF `current_price=0` / 無有效報價），要明講這是**資料完整性異常**，不要模糊寫成一般事件。
4. `market-view.md` 的 `體制轉換觸發條件` 也應把 major event 觸發列入本次原因。

## 建議寫法
- 活躍風險事件：
  - `資料完整性異常：00687B 無有效報價；00694B 無有效報價；00720B 無有效報價（L3）`
- 訊號變動歷史：
  - `| 2026-04-15T10:02+08:00 | 重大事件旗標 | 未記錄 | **L3 / 多項異常同時觸發** |`

## 更新順序
1. 先讀舊 wiki，抓前一版 `市場體制 / 風險溫度 / 風險事件`
2. 讀 `market_context_taiwan.json`、`market_event_context.json`、`major_event_flag.json`
3. 先判斷體制/風險是否變動
4. 再把 major event 轉成：
   - 報告中的異動事件
   - risk-signal 活躍風險事件
   - risk-signal 訊號變動歷史
   - market-view 體制轉換觸發原因

## 注意
- `major_event_flag.json` 的 `should_notify` 可為 false，但只要 `triggered: true`，wiki 仍應更新。
- 不要讓 `活躍風險事件` 漏掉這類資料異常，否則使用者只看到變動歷史，卻看不到目前正在作用中的風險。
- 產生 wiki 的 `最後更新` timestamp 時，若來源已是 `2026-04-15T11:01+08:00` 這種含時區 offset 的 ISO 字串，**不要再手動補一次 `+08:00`**，否則會寫出 `...+08:00+08:00` 的重複時區格式錯誤。
- `market_cache.json` 的 `quotes` 在實務上是 **dict keyed by symbol**（如 `quotes["0050"]`），不是 list；盤中報告抓 2-3 檔觀察標的時，應先按 symbol 取值，再用 `current_price` 與 `prev_close` 自算漲跌幅，避免因誤判 schema 導致觀察標的空白。
- `market_context_taiwan.json` 的 `quant_indicators` 目前採 **巢狀 schema**，不是平面欄位：應從 `rsi_distribution.avg / overbought_pct`、`macd_breadth.bullish_pct`、`sma_structure.above_sma20_pct`、`volatility.avg_annual` 取值；若誤讀成 `avg_rsi` / `overheated_ratio` / `macd_bullish_ratio` 這類平面鍵，wiki 會被寫成 0.0 假數值。
- `overbought_pct`、`bullish_pct`、`above_sma20_pct` 在實務上常是 **0~100 百分比數值**（例如 `93.3`），不是 0~1 ratio；寫 wiki 時不要再用 `%` 格式器乘一次 100，否則會出現 `9330%` 這種假數字。先判斷欄位是否大於 1，再決定直接顯示 `%` 或做 ratio 轉換。
- 更新 `risk-signal.md` 的 `訊號變動歷史` 時，不要用「抓所有 markdown table row」的寬鬆 regex 直接回收舊資料；這會把 `核心訊號表` 也誤塞進歷史表。應只保留真正以 ISO 時間開頭的歷史列（例如 `| 2026-04-15T12:01... |`）。

## 路徑解析（Pitfall）

- Cron 指令中的 `cd ~/.hermes/profiles/etf_master/skills/ETF_TW` 在 `terminal()` 工具中可能將 `~` 解析為 `/root/` 而非正確的 `/Users/tuchengshin/`，導致所有腳本 `No such file or directory`。
- **正確做法**：在 `execute_code` 或 `terminal()` 中，用 `find` 或 `$HOME` 先確認絕對路徑，或直接使用 `/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW`。
- 判斷方式：若 `cd` 失敗，先跑 `ls ~/.hermes/profiles/etf_master/skills/ETF_TW/.venv/bin/python` 確認路徑可達，若失敗則用 `find / -type d -name 'ETF_TW' 2>/dev/null` 定位。
