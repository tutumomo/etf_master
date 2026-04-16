# ETF_TW 穩定化計劃 — 交給 Code Agent 執行

## 0. 生效路徑（只改這些）

```
HERMES_HOME=~/.hermes/profiles/etf_master
ETF_TW_SKILL=~/.hermes/profiles/etf_master/skills/ETF_TW
DASHBOARD=~/.hermes/profiles/etf_master/skills/ETF_TW/dashboard
SCRIPTS=~/.hermes/profiles/etf_master/skills/ETF_TW/scripts
```

**禁止動** `~/.openclaw/` 下的任何檔案。

## 1. 真相層級（文件+程式必須一致）

分三層回答，不得混用：
- **Tier 1**：live API 直接查到的（list_positions / list_trades）
- **Tier 2**：live API 無法確認的（明講「無法確認」）
- **Tier 3**：state / dashboard / 記憶（明講「次級資訊」）

**掃除目標**：所有把 state/dashboard 說成「唯一真相源」或「持倉真相」的文案，改成上述三層分法。

重點檔案：
- `ETF_TW/SKILL.md`
- `ETF_TW/docs/AI_DECISION_BRIDGE.md`
- `ETF_TW/docs/BROKER_RECONCILIATION_RULES.md`
- `ETF_TW/docs/STATE_ARCHITECTURE.md`
- `ETF_TW/README.md`
- `etf-tw-live-query/SKILL.md`
- `etf-tw-order-submit-monitor/SKILL.md`

## 2. 交易保險絲（sizing + pre-flight + submit驗證）

### 2a. sizing_interface.py
- 預設值：`min_trade_unit=5`, `max_single_etf_pct=60`, `max_single_trade_pct=50`, `cash_buffer=5000`
- 輸出欄位：`quantity`, `quantity_mode`, `can_order`, `limit_reasons`, `sizing_engine`, `sizing_status`
- `quantity_mode` 必須是 `sizing_engine_v1`（不是 `placeholder_preview`）

### 2b. pre-flight gate
- 送單前一次全檢：股數>0、限價>0、can_order=true、集中度未超限、單筆未超限、交易時段正確、張/股單位正確、賣出不超持倉
- 買賣共用同一套 gate，不得有雙標

### 2c. submit≠落地
- `submit_order` 回應只代表 submit 階段訊號
- 正式回報必須有 `list_trades()` 佐證
- `list_trades()` 空值 = 本次查詢沒看到（不得反推沒送/已成交）

### 2d. 股/張與 order_lot
- Common：quantity = 股數 // 1000（張）
- IntradayOdd：quantity = 股數（股）
- 禁止用 `qty >= 1000 ? qty//1000 : 1` 這種舊寫法
- 禁止文件寫「非1000倍數一定拒絕」

重點檔案：
- `scripts/adapters/sinopac_adapter.py`
- `scripts/adapters/sinopac_adapter_enhanced.py`
- `scripts/sizing_interface.py`
- `scripts/run_auto_decision_scan.py`
- `scripts/generate_ai_agent_response.py`
- `scripts/generate_ai_decision_response.py`

## 3. 持倉交易票據 UI

### 3a. 持倉主列
- 只留核心欄位：代號、數量、均價、現價、損益、報酬率、一個「交易」按鈕
- 來源/狀態收進次級資訊（tooltip 或折疊）

### 3b. 交易票據 drawer
- 點「交易」展開，不放主列
- 內容：動作(買/賣)、股數、限價、模式(paper/live)、Preview 按鈕
- Preview 通過後才顯示確認字串 + 送出按鈕
- 不允許預覽即送單

### 3c. 送單後驗證
- submit 後自動跑 `list_trades()` 確認掛單存在
- 回報分層：live 看到 / 無法確認 / 次級資訊

重點檔案：
- `dashboard/app.py`（API endpoints）
- `dashboard/templates/overview.html`（UI）
- `dashboard/templates/base.html`（共用樣式）

## 4. 回歸測試

至少覆蓋：
1. 單位與 odd-lot（Common 張 / IntradayOdd 股）
2. list_trades 空回應語義（不得推論成沒送/已成交）
3. submit 成功但未落地（不得誤報成功）
4. 持倉票據 preview → confirm → submit 流程
5. sizing policy 變更可即時生效
6. 賣出股數超過持倉被擋
7. 單筆交易超過上限被擋

測試指令：
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m pytest tests/ -v
```

## 5. Git 規範

- 每個 phase 完成即 commit
- commit 訊息格式：`fix: 範圍 - 目的`
- 最後 push 並附 hash
- 禁止「已完成」但無 hash

## 6. 硬限制（不得違反）

1. 禁止混用 `~/.openclaw/` 與 `~/.hermes/profiles/etf_master/` 路徑
2. 禁止把 state/dashboard 當 live 事實
3. 禁止 submit 回傳成功就宣告委託落地
4. 禁止過時單位口號（非1000倍數一定拒絕）
5. 所有送單路徑必須走 pre-flight gate
6. 只改 active 路徑下的檔案

## 7. 回報格式（每個 phase）

```
## Phase N 完成
1. 做了什麼（3-6行）
2. 修改檔案（完整路徑）
3. 驗證命令與結果
4. 風險與回滾方式
5. commit hash
```