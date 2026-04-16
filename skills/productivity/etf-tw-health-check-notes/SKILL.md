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

### 巡檢 SOP 補充步驟

在原有 9 項之後新增第 10-12 項：

10. **測試可執行性**：`.venv/bin/python3 -m pytest tests/ -q --tb=short` 零 ERROR
11. **跨 State 一致性**：strategy_link ↔ regime_bucket_stats ↔ account_snapshot ↔ positions 四方對齊
12. **Cron 排程存在**：至少有盤前(08:45) + 盤後(15:00) 兩個核心排程