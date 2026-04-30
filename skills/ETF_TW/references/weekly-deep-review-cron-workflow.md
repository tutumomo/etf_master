---
name: etf-tw-weekly-deep-review
description: ETF_TW 每週深度復盤 cron 流程 — 週六執行，整合持倉快照、市場體制、ETF_TW 內建量化診斷、決策品質週報與下週操作傾向。
version: 1.0.0
created: 2026-04-25
tags: [etf-tw, cron, weekly-review, decision-quality, portfolio-review]
---

# ETF_TW 每週深度復盤流程

用於使用者要求「執行 ETF 每週深度復盤分析」或週六 cron 自動報告。目標是產出繁體中文、可審核、以持倉真相與決策品質為核心的週報。

## 觸發條件

- 使用者要求每週 ETF 深度復盤、週報、週六復盤
- cron 任務：週六上午執行
- 需要同時檢查：持倉、現金、配置、風險體制、決策品質、下週操作傾向

## 強制前置

1. 必須顯示策略抬頭：`[目前投資策略:XXX, 情境覆蓋:YYY]`
2. 報告必須用繁體中文。
3. 不做 live 下單；週報僅為分析與決策輔助。
4. 若資料來自 state / Yahoo Finance，須標註為本機快照或延遲資料，不可冒充即時券商真相。
5. 若 cron 無使用者在場，不得追問；缺資料就標註「資料缺失 / 信心較低」。

## 建議執行順序

優先用 `execute_code` 取得 `os.path.expanduser('~')` 後組絕對路徑；不要在 cron 裡假設 shell 的 `~` 指向正確 home。

```python
from pathlib import Path
import os, shlex
home = Path(os.path.expanduser('~'))
etf = home/'.hermes/profiles/etf_master/skills/ETF_TW'
stock = home/'.hermes/profiles/etf_master/skills/stock-analysis-tw'
py = etf/'.venv/bin/python3'
```

依序執行：

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 scripts/sync_market_cache.py
.venv/bin/python3 scripts/sync_ohlcv_history.py
.venv/bin/python3 scripts/sync_macro_indicators.py
.venv/bin/python3 scripts/sync_central_bank_calendar.py
.venv/bin/python3 scripts/generate_market_event_context.py
.venv/bin/python3 scripts/generate_taiwan_market_context.py
.venv/bin/python3 scripts/refresh_decision_engine_state.py
.venv/bin/python3 scripts/update_decision_outcomes.py
.venv/bin/python3 scripts/score_decision_quality.py
.venv/bin/python3 scripts/generate_decision_quality_report.py
.venv/bin/python3 scripts/generate_decision_quality_weekly.py
```

正常重點輸出：
- `MARKET_CACHE_SYNC_OK`
- `MARKET_INTELLIGENCE_OK`
- `MARKET_EVENT_CONTEXT_OK`
- `TAIWAN_MARKET_CONTEXT_OK`
- `DECISION_ENGINE_REFRESH_OK`
- `DECISION_OUTCOMES_UPDATE_OK`
- `DECISION_QUALITY_OK`
- `[quality-report] Generated: ...decision_quality_report.json`
- `GENERATE_DECISION_QUALITY_WEEKLY_OK:week=YYYY-WNN ...`

## ETF_TW 內建持倉診斷

從 `instances/etf_master/state/positions.json` 的 `positions` 陣列動態取 ticker，不要硬編碼。

轉換規則：
- `00679B` 等 B 結尾債券 ETF → `.TWO`
- 其他多數台股 ETF → `.TW`

```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python scripts/run_intraday_quant_diagnosis.py
uv run scripts/analyze_stock.py 0050.TW 0056.TW 006208.TW 00679B.TWO 00878.TW 00919.TW 00922.TW --fast --state-dir ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/stock_analysis
```

注意：`analyze_stock.py` 對台灣 ETF 信心度常偏低，因 ETF 無 earnings / analyst coverage / fundamentals。週報只把它作為技術風險與過熱提示，不作為完整買賣依據。

## 必讀 state 檔案

路徑：`ETF_TW/instances/etf_master/state/`

- `positions.json` — live_broker 持倉明細，鍵名通常是 `positions`
- `portfolio_snapshot.json` — 總資產、現金、市值、未實現損益；總資產以此為準
- `orders_open.json` — 是否有未完成掛單
- `agent_summary.json` — 策略抬頭、模式、摘要
- `market_context_taiwan.json` — 市場體制、風險溫度、群組趨勢、RSI 分布
- `market_event_context.json` — 外部事件與風險層
- `major_event_flag.json` — 重大事件是否觸發
- `decision_quality.json` — 近 7 日決策品質分數
- `decision_quality_report.json` — 累積決策品質報告
- profile wiki：`~/.hermes/profiles/etf_master/wiki/decision-weekly-YYYY-WNN.md`

## 重要資料結構坑

### positions.json

正確結構通常是：

```json
{
  "positions": [
    {"symbol": "0050", "quantity": 200, "average_price": 88.08, "current_price": 89.95, "market_value": 17990, "unrealized_pnl": 333}
  ],
  "source": "live_broker"
}
```

不要找 `holdings`；那是 `portfolio_snapshot.json` 的欄位。

### market_intelligence.json

正確結構是：

```json
{
  "updated_at": "...",
  "intelligence": {
    "0050": {"rsi": 71.1, "sharpe_30d": 2.9, ...}
  },
  "source": "..."
}
```

取指標時必須先進 `data['intelligence'][symbol]`，不是 `data[symbol]`。

部分欄位可能是 `NaN`，輸出前要轉成 `None` 或標註缺失，避免 JSON 或報告出現不可讀數字。

### weekly report 位置

`generate_decision_quality_weekly.py` 寫入 profile-level wiki：

```text
~/.hermes/profiles/etf_master/wiki/decision-weekly-YYYY-WNN.md
~/.hermes/profiles/etf_master/wiki/decision-quality-latest.md
```

不是 `ETF_TW/instances/etf_master/wiki/`。

## 可忽略但需記錄的警告

- `WARN: current process env missing AGENT_ID... Defaulting instance_id=etf_master`：cron 中常見，只要路徑明確且輸出 OK，可記錄但不阻斷。
- `sync_macro_indicators.py` 可能出現 Shioaji client name / seed 32 bytes / Solace 連線警告，但仍輸出 `MACRO_INDICATORS_OK`。若有 OK，週報標註 macro 部分使用 fallback / proxy 即可。
- Yahoo Finance 對部分 `.TWO` 或新 ETF 可能回報 possibly delisted / no data；只影響該標的資料信心，不代表真下市。

## 週報建議結構

```markdown
[目前投資策略:收益優先, 情境覆蓋:無]

📊 ETF 每週深度復盤分析｜YYYY-WNN
執行時間：YYYY-MM-DD HH:MM（台北）
資料來源：live broker 持倉快照、ETF_TW market context、decision provenance、stock-analysis-tw、Yahoo Finance 延遲資料

## 一、總結結論
- 市場體制 / 風險溫度
- 本週核心判斷：保留現金、避免追高、分批觀察等

## 二、目前資產配置
表格：標的 / 市值 / 總資產占比 / 未實現損益 / 報酬率
並摘要：現金比、核心型、收益型、防守型占比。

## 三、市場狀態復盤
- 平均 RSI
- MACD 廣度
- group trends：core / income / defensive / growth
- active events / top risks

## 四、持倉逐檔判斷
逐檔列出：續抱 / 不追高 / 小額分批 / 暫非首選。

## 五、本週決策品質復盤
引用 weekly md 與 decision_quality：
- 新增決策
- T1/T3/T10 回填
- finalized 樣本
- buy-preview vs hold
- direction/risk/opportunity/strategy alignment/confidence calibration 分數

## 六、下週操作建議
- 不追高名單
- 可觀察加碼順位
- 防守配置處理
- 現金水位建議
- 決策系統下週觀察重點

## 七、資料限制與注意事項
- yfinance 資料缺漏
- stock-analysis ETF confidence 偏低
- 無 live 下單 / 無掛單 / 僅分析
```

## 計算重點

### 總資產與權重

以 `portfolio_snapshot.json.total_equity` 為準：

```python
total_equity = snapshot['total_equity']
cash_weight = snapshot['cash'] / total_equity
symbol_weight = position['market_value'] / total_equity
pnl_pct = unrealized_pnl / (average_price * quantity)
```

### 配置分類

優先從 `market_context_taiwan.json.quant_indicators.group_trends` 與 watchlist / tape context 推導。若沒有 symbol→group map，可用保守備援：

- core：0050、006208、00922、00923
- income：0056、00878、00919、00929、00940、00713
- defensive：00679B、00687B、00694B、00720B
- growth：00830、00892、00935
- 其他：未分類，需標註

## 本次實測觀察（2026-04-25）

一輪完整週報實測可成功執行 12 個主要步驟，耗時約 100 秒。實測發現：

- `generate_decision_quality_weekly.py` 會同時嘗試門檻校正與 learned rules；樣本不足時會輸出跳過，這是正常狀態。
- stock-analysis-tw 對持倉 ETF 可跑通，但 ETF 報告多為 HOLD 且 confidence 8%-15%，原因是 ETF fundamental / analyst coverage 缺漏。
- 週報中應把 stock-analysis 的 overbought / RSI / near 52w high 當作風險提示，而不是把低 confidence 解讀成看空。
- 若 `decision_quality_report.json` 只有簡化欄位，不要硬要填 chain_breakdown；改用 weekly markdown 中的「雙鏈勝率」區塊，若 N/A 就誠實標 N/A。

## 最終原則

每週深度復盤的重點不是找一檔要買，而是回答四件事：

1. 目前持倉是否安全？
2. 現金水位是否足夠？
3. 市場體制是否允許加碼？
4. 決策系統本週有沒有變聰明或暴露問題？

若市場 `cautious + elevated`，預設結論應偏向「續抱、保留現金、不追高、小額分批觀察」。
