---
name: etf-tw-health-check-notes
description: ETF_TW 健康巡檢補充備忘 — 路徑修正、API 端點、已知模板 bug、cold start 問題
category: productivity
---

# ETF_TW Health Check 補充備忘

本技能是 etf-tw-health-check 的補充筆記，記錄 2026-04-16 巡檢時發現的差異。

## 路徑修正

SKILL.md 步驟 3 和 5 仍使用舊路徑 `/Users/tuchengshin/.openclaw/`，正確路徑為：
```
~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/
```

## venv 檢查修正

SKILL.md 說「不走 .venv/bin/python」，這是錯的。venv 內的 Python 可正常使用：
```bash
~/.hermes/profiles/etf_master/skills/ETF_TW/.venv/bin/python3 -c "import fastapi; print(fastapi.__version__)"
```
SKILL.md 中硬編碼的系統 Python 路徑過於脆弱，應改用 venv 路徑。

pip `Location` 可能顯示舊的 openclaw 路徑，這是 symlink 相容，不影響運行。

## Dashboard API 端點（實際已註冊）

以 app.py 為準，以下端點存在：
- GET `/` — 首頁
- GET `/health` — 健康檢查（非 /api/health）
- GET `/api/intelligence` — 市場情報
- GET `/api/overview` — 總覽
- GET `/api/history/{symbol}` — 歷史
- GET `/api/trade-journal` — 交易日誌
- POST `/api/strategy/update`, `/api/trading-mode/set`
- POST `/api/watchlist/add`, `/remove`
- POST `/api/refresh`
- POST `/api/ai-decision/*` — AI 決策
- POST `/api/trade/preview`, `/submit`
- POST `/api/auto-trade/config`, `/scan`, `/submit`

不存在（回 404）：`/api/state`, `/api/orders_open`, `/api/health`

## Dashboard 日誌

有兩個位置：
1. `~/.hermes/profiles/etf_master/skills/ETF_TW/dashboard.log` — 可能為空（0 bytes）
2. `/tmp/dashboard.log` — 實際錯誤日誌

巡檢時兩個都要檢查。

## Dashboard 進程檢查補充（2026-04-27）

Hermes `terminal()` 對 `ps aux | grep "uvicorn ..."` 或 `pgrep -af 'uvicorn...'` 可能誤判為「啟動長期 server/watch process」而拒絕執行。遇到這種 false positive 時，改用兩段式檢查：

```bash
lsof -i :5055 -P -n 2>/dev/null || true
ps -p <PID_FROM_LSOF> -o pid=,command= 2>/dev/null || true
```

確認只有 5055 正式 dashboard LISTEN；5050/5051 若存在仍視為殘留舊實例。

## 已知模板 Bug

overview.html 第 333 行引用 `data_sources` 變數，但路由未傳入，導致：
```
jinja2.exceptions.UndefinedError: 'data_sources' is undefined
```
首頁仍回 HTTP 200（可能有 fallback），但渲染可能不完整。

## portfolio_snapshot Cold Start 問題

`/health` 可能回報「持倉與資產快照不一致」，原因：
- `portfolio_snapshot.json` 被 cold_start 重新初始化，holdings=[], cash=0
- 但 `positions.json` 仍保留舊資料
- snapshot 的 `source` 欄位為 `"cold_start_initialization"`

修復方式：觸發 state 同步或 broker API live reconciliation。

## 2026-04-16 階段性改造巡檢新增項目

以下為 v1.3.5 大改造後首次全面巡檢發現的問題，未來巡檢應納入。

### CLI `search` 子命令回歸異常（2026-04-19）

實測：
```bash
.venv/bin/python3 scripts/etf_tw.py search 0050
```
會拋出：
```text
KeyError: 'summary'
```
根因是 `cmd_search` 直接存取 `etf["summary"]`，但 ETF 資料集中部分項目沒有 `summary` 欄位。

**巡檢規則補充**：
- 健檢時不要只跑 `check`，需額外跑一次 `search` 煙霧測試。
- 在 bug 修復前，查標的請改用：
```bash
.venv/bin/python3 scripts/etf_tw.py universe-search 0050 --limit 5
```
- `compare`、`universe-list`、`universe-search` 可作為 CLI 基本可用性替代驗證。

### 測試 Import 路徑崩壞

`test_fuse_v1.py` 和 `test_sizing_v1.py` 使用 `from skills.ETF_TW.scripts.xxx import yyy`，
但 Hermes profile 目錄下沒有 `skills.ETF_TW` 這個 Python package。150 個測試檔中僅 2 個被嘗試載入，且全失敗。

修正方向：測試 import 應用 `sys.path` 注入或 `from scripts.xxx`，不要用全限定包名。
巡檢時應跑 `.venv/bin/python3 -m pytest tests/ -q --tb=short` 並確認零 ERROR。

### decision_log 去重閘門漏網

`_session_dedup_key()` 在 date/symbol 欄位缺失時產生 `?` 鍵值，導致去重失效。
2026-04-16 實測：10 筆中有 6 筆重複（00923×2, 006208×2, 00830×2）。

巡檢時應檢查：
```bash
cat state/decision_log.jsonl | python3 -c "
import sys,json; from collections import Counter
keys=[]
for l in sys.stdin:
    d=json.loads(l.strip())
    keys.append(f\"{d.get('date','?')}|{d.get('symbol','?')}|{d.get('action','?')}\")
dupes={k:v for k,v in Counter(keys).items() if v>1}
print(f'Duplicates: {dupes}' if dupes else 'No duplicates')
"
```

### 跨 State 一致性檢查（新增 3 項）

1. **strategy_link vs regime_bucket_stats**：strategy 變更後 regime_bucket 可能仍為舊策略快照。
   - 檢查：兩者的 base_strategy 應一致
2. **account_snapshot vs positions**：account_snapshot.market_value 可能為 0（未計入持倉市值）。
   - 檢查：account_snapshot.market_value 應 ≈ sum(positions[].market_value)
3. **decision_quality.anomaly_hit_rate**：若 anomaly_hit = decision_count（如 9/9），閾值可能過敏感。

### Cron 任務全空

SKILL.md 列了 8 個排程，但 `~/.hermes/cron/jobs/` 可能为空。
巡檢時必查 `ls ~/.hermes/cron/jobs/ | wc -l`，若為 0 應標記為 P2+ 問題。

### Dashboard app.py 已知代碼問題（2026-04-17 巡檢）

以下為通讀 `dashboard/app.py`（1407 行）發現的問題，未來修改時應一併處理：

#### 🔴 P1：`_run_full_pipeline_helper()` 重複定義（死碼）
- L1181-1199：第一版（簡陋，無 lock）
- L1205-1251：第二版（有 lock、完整管線）
- Python 使用後者覆蓋前者，L1181-1199 為死碼，應刪除

#### 🟡 P2：管線腳本用 `sys.executable` 而非 `PYTHON_VENV`
- L1233：`'{sys.executable}'` 在 f-string 裡，若 dashboard 非 venv python 啟動會跑錯 Python
- 違反鐘律7（venv 強制檢查），應改為 `'{PYTHON_VENV}'`

#### 🟡 P2：`lot_type` 門檻硬編碼 1000
- L1071：`"lot_type": "board" if payload.quantity >= 1000 else "odd"`
- L1118 同樣邏輯重複
- 與教訓33（張/股地雷）相關，門檻應由 adapter 決定而非 dashboard 硬編

#### 🟢 P3：`classify_freshness()` timezone 邊界
- L536：`datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()`
- 若 state 檔 timestamp 格式不一致（有時帶 TZ 有時不帶），可能有偏差
- 目前實務上 OK，但未來 state 檔若改格式需注意

#### 🟢 P3：多餘空行
- L525-527 三行空行，美觀問題

### 巡檢 SOP 補充步驟

在原有 9 項之後新增第 10-13 項：

10. **測試可執行性**：`.venv/bin/python3 -m pytest tests/ -q --tb=short` 零 ERROR
11. **跨 State 一致性**：strategy_link ↔ regime_bucket_stats ↔ account_snapshot ↔ positions 四方對齊
12. **Cron 排程存在**：至少有盤前(08:45) + 盤後(15:00) 兩個核心排程
13. **Dashboard 死碼掃描**：`grep -n "def _run_full_pipeline_helper" dashboard/app.py` 應只出現一次；檢查 `sys.executable` 是否在管線腳本呼叫中被誤用

## 2026-04-19 新增：財經技能→Wiki 引用鏈路實測備忘

### A) `distill_to_wiki.py` 沒有 `--help`，帶參數會直接執行更新

- `scripts/distill_to_wiki.py` 沒有 argparse，執行 `--help` 不會顯示說明，而是**直接跑主流程**。
- 巡檢時若只想測可執行性，不要帶 `--help`，改用：
  - 先讀原始碼確認入口 (`read_file scripts/distill_to_wiki.py`)
  - 或先對 wiki 檔案做 mtime 快照，再執行一次並比對（確認是否真的寫入）

### B) Wiki 寫入目標有「雙路徑」，不要搞混

`distill_to_wiki.py` 的 `_get_wiki_dir()` 解析順序：
1. 讀 `~/.hermes/profiles/etf_master/config.yaml` 的 `skills.config.wiki.path`
2. 若無或無效，fallback 到 `~/.hermes/profiles/etf_master/wiki`

這與 `ETF_TW/instances/etf_master/wiki/`（market-view / risk-signal）是不同用途。

- `instances/etf_master/wiki/`：盤中判讀頁（`market-view.md`, `risk-signal.md`）
- `~/.hermes/profiles/etf_master/wiki/entities/`：llm-wiki entity 頁（由 distill_to_wiki 更新）

### C) 鏈路驗證最小檢查（可重用）

1. `uv run skills/stock-market-pro-tw/scripts/yf.py price 0050.TW`（報價來源）
2. `uv run skills/stock-analysis-tw/scripts/analyze_stock.py 0050.TW --fast --state-dir <ETF_TW state>`（分析吃 state）
3. `cd skills/ETF_TW && .venv/bin/python3 scripts/distill_to_wiki.py`（知識沉澱）
4. 檢查 `~/.hermes/profiles/etf_master/wiki/entities/*0050*.md` 是否有：
   - `## 最新市場數據快照`
   - `> 自動更新於 ...`
   - `| 現價 | NT$ ... |`

### D) 實測事實（2026-04-19）

- `distill_to_wiki` 實際更新了 `~/.hermes/profiles/etf_master/wiki/entities/0050-yuanta-taiwan-50.md`
- 並非寫入 `ETF_TW/instances/etf_master/wiki/`