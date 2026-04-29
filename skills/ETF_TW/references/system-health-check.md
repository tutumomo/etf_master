---
name: etf-tw-health-check
description: ETF_TW 系統健康巡檢技能 — dashboard、state、venv、API 端點檢查
category: productivity
---

# ETF_TW 健康巡檢技能

## Trigger
當需要執行 ETF_TW 系統健檢（dashboard、state、venv），或用戶說「健康巡檢」、「檢查 ETF_TW」時使用。

## 目錄結構（已確認路徑，2026-04-14 驗證）

| 組件 | 路徑 |
|------|------|
| Skill 根目錄 | `~/.hermes/profiles/etf_master/skills/ETF_TW/` |
| Instance State | `~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/` |
| Private 憑證 | `~/.hermes/profiles/etf_master/skills/ETF_TW/private/.env` |
| CA 憑證 | `~/.hermes/profiles/etf_master/skills/ETF_TW/private/certs/sinopac_ca_new.pfx` |
| Dashboard 根 | `~/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/` |
| 運行日誌 | `~/.hermes/profiles/etf_master/skills/ETF_TW/dashboard.log` |

**正確登入流程**（憑證讀取方式見 SKILL.md 血淚教訓）：
- 從 `private/.env` 用 Python `open()` + `line.split('=', 1)` 讀取明文
- `shioaji.login()` 不吃 `ca_path`；CA 啟用需單獨呼叫 `api.activate_ca()`
- CA 密碼從 env 讀取，禁止硬編碼

## 巡檢步驟

### 1. Dashboard 存活檢查
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5055/
# 預期：200
```

### 2. 檢查 uvicorn 程序
```bash
ps aux | grep "uvicorn dashboard.app:app --host 0.0.0.0 --port 5055" | grep -v grep
```
注意：Python 3.14，路徑為 `...Python.framework/Versions/3.14/...`

### 3. AGENT_ID / OPENCLAW_AGENT_NAME 環境檢查（消除 instance fallback 警告）
```bash
env | egrep '^(AGENT_ID|OPENCLAW_AGENT_NAME|HERMES_HOME)='
```
若只看到 `HERMES_HOME`、卻沒有 `AGENT_ID` / `OPENCLAW_AGENT_NAME`，執行 ETF_TW 指令時會出現：
`WARN: AGENT_ID (or legacy OPENCLAW_AGENT_NAME) missing; defaulting instance_id=etf_master`

**修復方式**：
- 單次執行：`AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py ...`
- 目前 shell：`export AGENT_ID=etf_master`
- 永久（建議）：寫入 `~/.zshrc` 後 `source ~/.zshrc`
- 服務/排程（最穩）：在 `start_dashboard.sh` 與 cron 指令前綴注入 `AGENT_ID=etf_master`

### 4. State 檔案新鮮度
```bash
ls -lht ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/*.json
```
檢查最新修改時間是否在合理範圍內（交易時段後應在數分鐘內更新）。

### 4. Dashboard 日志（找 API 404）
```bash
tail -20 /tmp/dashboard.log
```
常見問題信號：
- `404 Not Found` on 舊端點（如 `/api/positions`、`/api/kpi`、`/api/orders-open`、`/api/health`）→ 多半是有人還在用舊版 API 路由；新版應以 `/api/overview`、`/api/intelligence`、`/api/refresh`、根路徑 `/health` 為準
- 多筆 `showGlobalBanner` JS 錯誤（交易模式切換失敗等）

### 5. Auto Trade State
```bash
cat ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/auto_trade_state.json
```
確認 `live_submit_allowed`、`preview_only_mode` 是否符合預期。

### 6. venv 驗證
不走 `.venv/bin/python`，直接用系統 Python import：
```bash
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -c "import fastapi; print(fastapi.__version__)"
```

## 常見異常與原因

| 異常 | 可能原因 |
|------|----------|
| State 超過 17 小時未更新 | cron auto-refresh 未觸發，或 API 異常 |
| `/api/state` 404 | dashboard/app.py 中端點未註冊 |
| Dashboard HTTP 非 200 | uvicorn 進程斷裂或端口衝突 |
| 前端報「交易模式切換失敗」 | backend API 端點缺失 |
| State 持倉與 broker API 不符 | **state 是次級快照，broker API 是真相源，須以 live API 為準** |
| `/health` 回傳 ok:false | 非交易時段 state 未更新導致新鮮度判定為 warn，屬正常行為 |
| worldmonitor 快照全為 "unknown" | 資料源解析問題或 API 限制，需檢查 sync_worldmonitor_daily.py 抓取邏輯 |
| account_snapshot.total_equity == cash | 已知 Shioaji API bug：balance.market_value 回傳 0 被直接寫入；portfolio_snapshot.total_equity 才是正確值 |

## ⚠️ State vs Broker 真相對帳（2026-04-14 血淚驗證）

**情境**：state/positions.json 顯示 00679B/00878/00919 各 100 股，但 Shioaji `list_positions()` 回 0 股。
只有 0050（253股）是真的，state 和 broker 完全不符。

**原則**：
1. **broker live API 優先於 state 檔案**，但回答時仍要誠實標記其限制；若 `list_positions()` / `list_trades()` 結果自相矛盾或明顯異常，不得硬判為最終真相
2. **ghost order 判定**：訂單 `broker_order_id=null` + `verified=false` = 從未送達券商的幽靈單
   - 發現後立即從 state 清除，並通知用戶
3. **每次查持倉時，必須同時查 broker live API**，並把「本次 API 直接看到」與「次級資料推定」分開說
4. **positions.json 可能是 snapshot 而非 truth**；但當 live API 也不足以確認時，應直接承認無法確認，而不是用 state 補成既成事實

**標準備查指令**：
```python
api = sj.Shioaji(); api.login(...); api.activate_ca(...)
# 掛單驗證
trades = api.list_trades()
for t in trades: print(f"{t.id} | {t.contract.symbol} | {t.status.status}")
# 持倉驗證
positions = api.list_positions(api.stock_account)
for p in positions: print(f"{p.code} | qty={p.quantity} | avg_cost={p.price}")
bal = api.account_balance(api.stock_account)
print(f"現金: {bal.acc_balance} TWD")
api.logout()  # 注意：logout 可能 segfault，忽略即可
```

**State 檔案位置**：`~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/`
- positions.json
- orders_open.json
- portfolio_snapshot.json
- agent_summary.json

## 階段性改造覆核流程（Post-Renovation Review）

當 Gemini CLI 或其他 code agent 修改完 ETF_TW 後，執行以下覆核：

### R1. 測試套件
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -30
```
- 記錄 passed/failed 數量
- 失敗測試依根因分類：import路徑、斷言值偏移、模板/文件不匹配、架構變更未同步

### R2. State 資料品質深度檢查
- **decision_log 必填欄位**：date/symbol 不能 MISSING，否則去重閘門全廢
- **account_snapshot.market_value**：不應為 0，應 ≈ positions.json 各持倉 market_value 之和。Shioaji API `balance.market_value` 可能回傳 0，`sync_live_state.py` 直接用 API 值寫入 account_snapshot 導致 market_value=0。解法：在 `sync_portfolio_snapshot.py` 成功後回寫 account_snapshot 的 market_value（從 positions 加總），或讓 dashboard 直接用 portfolio_snapshot 的 market_value
- **strategy 與 regime_bucket 一致性**：strategy_link 的 base_strategy 必須與 regime_bucket_stats 的 strategy.base_strategy 相同，不同 = stats 過期需重建

### R3. Cron 排程檢查
- 預期 ≥5（盤前/盤中/盤後/健康/週復盤）
- 0 = 全部丟失，需重建

### R4. Git 變更追蹤
- `git log --oneline -10` 確認 code agent 的 commit 都在
- `git diff HEAD~5 --stat` 看改了哪些檔

### R5. 覆核評分表
| 維度 | 滿分 | 評估重點 |
|------|------|----------|
| 架構完整性 | 10 | State/Dashboard/決策引擎/共識仲裁是否到位 |
| 資料品質 | 10 | decision_log欄位完整、snapshot市值正確、strategy一致 |
| 測試覆蓋 | 10 | passed數 + 失敗根因分類 |
| 自動化運行 | 10 | Cron排程數量與正確性 |
| 安全性 | 10 | 幽靈掛單、venv強制、風控閘門 |

### 常見 Code Agent 修不好或漏修的項目
- **decision_log 的 date/symbol 缺失**：去重閘門依賴這兩欄，缺了等於閘門全廢
- **confidence 降級偏移**：改了信心度公式但測試期望值沒同步
- **regime_bucket_stats 過期**：strategy 切換後 stats 沒跟著刷
- **Cron 重建**：code agent 通常不會主動建 Hermes cron
- **測試 mock 路徑**：`from skills.ETF_TW.scripts.xxx` 在 Hermes profile 下不存在
- **Dashboard README 缺關鍵腳本提及**：測試會檢查 README 含 `sync_agent_summary.py` 和 `agent_summary.json`，code agent 容易漏補這類文檔
- **測試全過 ≠ 資料正確**：269 passed 只代表邏輯正確，不代表 state 檔案內容正確（舊 decision_log 的 date/symbol 仍 MISSING）

## Worldmonitor 升級驗收重點（v1.4+）

當 ETF_TW 接入 worldmonitor 後，健康巡檢需新增以下驗收：

- 不能只看 worldmonitor 專屬測試，還要看全測試是否全綠；若全測試有失敗，結論必須標記為「尚未完整落地」。
- 需交叉驗證三個輸出面：
  1) worldmonitor 快照檔是否更新
  2) dashboard 全球風險 API 是否與快照一致
  3) AI decision request 是否包含 worldmonitor context
- Watch 模式有高風險路徑坑：若在 skill root 下再拼接一層 `skills/ETF_TW`，會導致 L3 事件升級時無法觸發後續 major event 機制。
- 發版前需檢查 SKILL/README/CHANGELOG 三者版本與功能敘述一致，避免文件版本漂移。
- worldmonitor 輸入源序號描述要和實際 payload 一致（避免文件寫第 13，但實作已是第 14）。

## Wiki / 財經鏈路健檢（新增，2026-04-19）

當用戶要求「檢查 ETF_TW 是否有正常引用財經技能與 wiki」時，除了 API/State 健檢，必做以下鏈路驗證：

### W1. ETF_TW 核心可用性（最小 smoke）
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py check
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py compare 0050 00878
AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py search 0050
```

### W2. 財經技能可調用性（不是只有檔案存在）
```bash
uv run ~/.hermes/profiles/etf_master/skills/stock-analysis-tw/scripts/analyze_stock.py --help
uv run ~/.hermes/profiles/etf_master/skills/stock-market-pro-tw/scripts/yf.py --help
```
並檢查 `skills/taiwan-finance/references/*.md` 是否完整可讀。

### W3. Wiki 注入鏈路真實驗證
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
AGENT_ID=etf_master .venv/bin/python3 scripts/generate_ai_decision_request.py
python3 - <<'PY'
import json
p='instances/etf_master/state/ai_decision_request.json'
d=json.load(open(p))
print('wiki_context keys=', list((d.get('wiki_context') or {}).keys()))
print('market_view length=', len(((d.get('wiki_context') or {}).get('market_view') or '')))
print('entities count=', len(((d.get('wiki_context') or {}).get('entities') or {})))
PY
```

### W4. 斷鏈判定規則（2026-04-19 實戰）
若出現以下任一情況，判定為「wiki 引用鏈路異常」：
1. `ai_decision_request.json` 的 `wiki_context.market_view` 為空字串
2. `wiki_context.entities` 長期為空（且持倉有 ETF）
3. 腳本硬編碼路徑與實際 wiki 根目錄不一致（例如腳本讀 `docs/wiki/shioaji`，但實際在 `~/.hermes/profiles/etf_master/wiki/`）
4. entity 檔名規則不一致（腳本假設 `{symbol}.md`，實際為 slug，如 `0050-yuanta-taiwan-50.md`）

### W5. 回報分層（誠實）
- A. ETF_TW 主功能是否正常（check/compare/search/dashboard）
- B. 財經技能是否「可調用」
- C. ETF_TW 是否真的「有吃到 wiki」

避免把「技能可調用」誤報成「ETF_TW 已完成跨技能自動鏈接」。

## Dashboard 原始碼審計（Code Audit Checklist）

當需要深度檢查 `dashboard/app.py` 或相關 Python 檔案的程式碼品質時，依以下清單掃描：

### A. 死碼偵測
```bash
# 1. 重複定義（Python 靜默覆蓋，前者變死碼）
grep -n "^def " dashboard/app.py | awk -F: '{print $2}' | sort | uniq -d

# 2. 重複 import
grep -n "^import " dashboard/app.py | sort | uniq -c | sort -rn | head

# 3. 殘留檔案（功能已整合進 app.py 的 patch 檔）
find dashboard/ -name "app_patch.py" -o -name "*.bak"
```

### B. 函數參數活性檢查
```bash
# 找出接受參數但內部從未使用的函數
# 例：dashboard_health.py 的 classify_freshness 參數曾經是死參數
grep -n "classify_freshness" scripts/dashboard_health.py
```
**方法**：對每個接受 callback 參數的函數，確認函數體內實際使用了該參數，而非用自己的內部版本替代。

### C. Python 直譯器一致性
```bash
# 檢查 subprocess 呼叫用 sys.executable 還是 PYTHON_VENV
grep -n "sys\.executable\|PYTHON_VENV" dashboard/app.py
```
**規則**：
- 啟動子進程跑 ETF_TW 腳本（需 etf_core 等自訂模組）→ **必須用 PYTHON_VENV**
- `PYTHON_VENV = Path(sys.executable)` (L49) 是 venv 找不到時的 fallback，非設計入口
- notify_agent_*.py 只用 stdlib → sys.executable 理論上可以，但為一致性仍應用 PYTHON_VENV
- shell cmd f-string 裡的 `{sys.executable}` 也要改 → `'{PYTHON_VENV}'`

### D. 時區安全
```bash
# 找出直接用 datetime.now() 假設本地時區 = 台灣時區的地方
grep -n "datetime.now()\.astimezone()\|datetime\.now()\.hour\|datetime\.now()\.weekday" dashboard/app.py
```
**修正**：改用 `datetime.now(ZoneInfo("Asia/Taipei"))` 確保不受系統時區影響（Docker/CI 常是 UTC）。

### E. classify_freshness 門檻一致性
```bash
# 兩處定義必須門檻一致
grep -A5 "def classify_freshness\|def classify_health_freshness" dashboard/app.py scripts/dashboard_health.py
```
**目前門檻**：≤24hr=good, 24~48hr=warn, >48hr=bad
**設計原則**：收盤後不更新是正常行為，10min/1hr 的舊門檻會誤判。

### F. lot_type 門檻散佈檢查
```bash
# >= 1000 的硬編碼散佈在多處，未來改一處漏一處
grep -rn "lot_type.*1000\|>= 1000.*odd\|>= 1000.*board" dashboard/ scripts/
```
**已知位置**：app.py L1071/L1118, base.py L177, etf_tw.py L105/L652

### G. Template 資料浪費檢查
```bash
# build_overview_model() 傳入 template 但 template 沒引用的欄位
grep -c "freshness" dashboard/templates/overview.html  # 0 = 白傳
```

## Cron 排程維運檢查

### C1. Hermes Cron 排程檢查（非系統 crontab）

ETF_TW 排程走 Hermes cron 系統，非 `crontab -l`。資料在：
```
~/.hermes/profiles/etf_master/cron/jobs.json
```

解析方式（JSON 含 unicode escape，需 python 解碼）：
```bash
python3 << 'PYEOF'
import json
with open('$HOME/.hermes/profiles/etf_master/cron/jobs.json') as f:
    jobs = json.load(f)['jobs']
for j in jobs:
    model = j.get('model') or 'null(None)'
    script = j.get('script') or 'null'
    lr = j.get('last_run_at') or 'NEVER'
    ls = j.get('last_status') or 'NEVER'
    print(f"{j['name']} | sched={j.get('schedule_display','?')} | model={model} | last={lr} | status={ls}")
PYEOF
```

LLM 型 cron 任務若未指定 model/provider，會 fallback 到系統預設（可能已失效如 openai-codex 429）。檢查：
- model=null 的 LLM 型任務（非 script 型）需明確設定 `ollama-cloud/glm-5.1:cloud`
- script 型任務不需 model，但需確認 AGENT_ID 前綴
- model=null 的 LLM 型任務（非 script 型）需明確設定 `ollama-cloud/glm-5.1:cloud`
- script 型任務不需 model，但需確認 AGENT_ID 前綴

### C2. 從未執行的任務
- `last_run_at: null` + `last_status: null` = 從未成功執行
- 解法：手動 `cronjob(action='run')` 觸發一次，確認腳本 exit 0
- worldmonitor script 型任務需確認 snapshot 檔案有更新時間戳
- 已知案例：「ETF 決策自動復盤」和「ETF 決策品質週報」自建立後從未執行，需手動觸發驗證

### C3. Dashboard 殘留進程
```bash
lsof -i :5050 -i :5051 -i :5055 -P -n
```
- 只有 5055 是正式 dashboard；5050/5051 是殘留舊實例，直接 kill
- 啟動前先清：`lsof -i :5055 -t | xargs kill 2>/dev/null`

### C4. 新端點 404 排查
- 新增路由後 dashboard 未重啟 → 舊進程跑舊 app.py → 404
- 排查：確認端點在 app.py 有定義 → 重啟 dashboard → 順手清殘留 port

## Memory 定期清整原則

當 memory 使用量 >50% 時，應主動清整：
1. **SKILL.md 已收錄的教訓** → 刪（SKILL.md 是 single source of truth）
2. **重複條目** → 合併為精簡版
3. **一次性任務備忘**（路徑、暫存檔）→ 刪
4. **環境變數/API 奇怪行為** → 保留（易再犯）
5. **user profile 重複偏好** → 合併為一條
6. 清整後回報：刪除幾條、保留幾條、使用率變化

## 巡檢回報格式
1. Dashboard 狀態（HTTP code、程序是否存在）
2. State 新鮮度（最新更新時間 vs 現在時間）
3. API 端點健康（日誌中有無 404）
4. Auto Trade 設定合理性
5. Cron 排程健康（模型設定、執行狀態、殘留進程）
6. 建議（分緊急/次要）
