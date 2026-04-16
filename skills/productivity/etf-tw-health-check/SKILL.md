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

### 3. State 檔案新鮮度
```bash
ls -lht ~/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/*.json
```
檢查最新修改時間是否在合理範圍內（交易時段後應在數分鐘內更新）。

### 4. Dashboard 日志（找 API 404）
```bash
tail -20 /tmp/dashboard.log
```
常見問題信號：
- `404 Not Found` on `/api/state`、`/api/orders_open`、`/api/health` → 前端依賴的端點未註冊
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
- **account_snapshot.market_value**：不應為 0，應 ≈ positions.json 各持倉 market_value 之和
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

## 巡檢回報格式
1. Dashboard 狀態（HTTP code、程序是否存在）
2. State 新鮮度（最新更新時間 vs 現在時間）
3. API 端點健康（日誌中有無 404）
4. Auto Trade 設定合理性
5. 建議（分緊急/次要）
