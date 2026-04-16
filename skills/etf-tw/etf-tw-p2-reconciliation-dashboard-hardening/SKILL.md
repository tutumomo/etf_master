---
name: etf-tw-p2-reconciliation-dashboard-hardening
description: ETF_TW P2 深修流程：資料流審計、訂單監控/filled reconciliation 升級、dashboard source label 視覺化、決策層 placeholder 降級
---

# ETF_TW P2 Reconciliation + Dashboard Hardening

## 何時使用
- 使用者要求「把系統再收乾淨一輪」
- 已完成 P0（真相源、ghost order、submit≠落地）後，進一步修 dashboard / reconciliation / decision layer
- 發現 dashboard 還看不出 live vs fallback
- 發現 fill detection 仍過度依賴 `list_trades()` 或 symbol 級對帳太粗
- 發現 preview quantity 看起來像正式 sizing

## 核心目標
1. 把資料層角色畫清楚：live API / state / dashboard / agent
2. 把 fill detection 從「過度自信」降到「證據分級」
3. 把 filled reconciliation 從 symbol 級升為 order 級
4. 讓 dashboard 畫面直接看得出 source / fallback
5. 把 preview quantity placeholder 正式降級標示，避免被當成 sizing

---

## Phase A：資料流審計（P2-1）

### 要查的核心檔案
- `dashboard/app.py`
- `scripts/state_reconciliation.py`
- `scripts/state_reconciliation_enhanced.py`
- `scripts/diag_state_sources.py`
- `scripts/complete_trade.py`
- `scripts/orders_open_state.py`

### 要產出的結論
把資料正式分成四層：
- Layer A: broker live API（優先查證層）
- Layer B: instance state（system-of-record / reconciliation 層）
- Layer C: dashboard（展示 / fallback 組裝層）
- Layer D: agent 回答（誠實翻譯層）

### 重要教訓
- instance state 不能被說成對外回答的唯一真相
- dashboard fallback 不能被說成 live query
- agent 最容易把 A/B/C 三層混成一句話

---

## Phase B：訂單監控與 Fill Detection 深修（P2-2）

### 危險訊號
如果看到以下情況，要立即收斂：
- `poll_order_status.py` 依賴 `adapter.get_trades()`，但 BaseAdapter 根本沒定義這個介面
- 舊監控腳本直接把 `list_trades()` 當成交事實來源
- broker 查不到就直接斷言失敗 / 已成交

### 正確修法

#### 1. 重寫 `poll_order_status.py`
改成：
- 優先走 `adapter.get_order_status(order_id)`
- 若 broker 查不到，但持倉數量變化足以支持，才用 position delta 做保守 filled 推定
- 不再依賴不存在的 `get_trades()`
- 不再把空查詢直接解讀成失敗或成交

#### 2. Fill Detection 證據分級
- A級：broker 明確證據（`get_order_status()` 查到 filled/partial_filled）
- B級：position delta 保守推定（只在 baseline qty + target qty 足以支持時）
- C級：無法確認（不能硬判）

#### 3. 舊監控腳本直接停用
如果有 `~/.hermes/scripts/order_monitor.py` 這種 legacy 腳本，且它：
- 依賴 legacy state
- 硬編碼監控標的
- 過度信任 `list_trades()`

就直接改成停用警告，不要留半套：
- 輸出「已停用」
- 引導改用 `ETF_TW/scripts/poll_order_status.py`
- 輸出 `HERMES_CRON_TERMINATE=true`

---

## Phase C：Filled Reconciliation 從 symbol 級升為 order 級

### 舊問題
`filled_reconciliation.py` 若只回：
- `unreconciled_symbols`
- `unreconciled_count`

粒度太粗，使用者只知道哪個 symbol 有問題，不知道哪筆 order 出問題。

### 新 schema（向後相容）
保留舊欄位，再新增：
- `unreconciled_orders`
- `unreconciled_order_count`

每筆 `unreconciled_orders` 至少包含：
- `order_id`
- `symbol`
- `status`
- `filled_quantity`
- `position_quantity`
- `issue`
- `source_type`
- `observed_at`

### 最低判定邏輯
- `status == filled` 但 `position_quantity < filled_quantity` → `filled_qty_exceeds_position_qty`
- `status == partial_filled` 且 `filled_quantity > 0` 但 position 完全沒有 → `partial_fill_missing_position_presence`
- symbol 缺失 / positions 無此 symbol → 對應 issue

### 向後相容鐵律
不要直接刪掉：
- `unreconciled_symbols`
- `unreconciled_count`

因為 dashboard / tests / 其他流程可能還在讀。
先新增 order 級欄位，再讓舊欄位由新結果推導。

---

## Phase D：Dashboard source label 視覺化（P2-4）

### API 層
先在 `dashboard/app.py` 的 `build_overview_model()` 補：
- `data_sources.positions`
- `data_sources.orders_open`
- `data_sources.portfolio_snapshot`
- `data_sources.agent_summary`
- `data_sources.filled_reconciliation`

對 `positions` 額外補：
- `is_fallback`

### 前端層
再改：
- `dashboard/templates/base.html`
- `dashboard/templates/overview.html`

### 視覺規則
做成色塊而不是裸文字：
- 綠色：`source-live` / `live-preferred`
- 藍色：`source-state`
- 黃色：`source-fallback`

### 至少要顯示在
- 總資產卡
- 持倉快照卡
- 狀態中心
- Filled Reconciliation 區塊
- 決策區（Rule Engine / AI Bridge / auto_preview_candidate）

### 決策區第三輪視覺化（這輪新增）
除了 source badge，還要把這些狀態做成一眼可辨識的 badge：
- `preview-locked` → 黃色 LOCKED
- `preview-low-confidence` → 黃色 LOW CONFIDENCE
- 其他 preview mode → 綠色 / 正常 preview badge
- AI Bridge `Fresh / Stale / 尚無` 也做 badge，不只裸文字
- `quantity_mode`（如 `placeholder_preview`）要直接顯示在決策建議區
- `sizing_engine / sizing_status` 要一起顯示，避免使用者以為已做正式 sizing
- `consensus.tier / resolved / confidence_level` 要直接顯示，不要埋在 JSON 裡

### 驗證點
- `overview.html` Jinja 可正常解析
- `/api/overview` 有 `data_sources`
- 畫面不是只有文字「來源」，而是有視覺可辨識的 badge

---

## Phase E：決策層 placeholder 降級（P2-3 深修）

### 危險訊號
如果這些檔案仍直接寫：
- `quantity: 100`

就很容易讓人誤以為系統做過 sizing：
- `scripts/run_auto_decision_scan.py`
- `scripts/generate_ai_agent_response.py`
- `scripts/generate_ai_decision_response.py`

### 正確修法
保留 `quantity=100` 當暫時 placeholder，但必須明確降級：
- `quantity_mode: "placeholder_preview"`
- `quantity_note: 此數量僅為 preview placeholder，尚未做正式 sizing，不可直接視為正式建議股數`

### 原則
- 不要假裝已有 sizing engine
- 先誠實降級，再未來接 `sizing_engine_v1`

### 這輪新增的可重用做法
不要只在各檔案散落塞：
- `quantity_mode`
- `quantity_note`

而是直接抽成共用介面，例如：
- `scripts/sizing_interface.py`
- `build_placeholder_preview_sizing()`

最低輸出欄位：
- `quantity`
- `quantity_mode = "placeholder_preview"`
- `sizing_engine = "sizing_engine_v1"`
- `sizing_status = "not_configured"`
- `quantity_note`

然後在這 3 條決策鏈統一接入：
- `run_auto_decision_scan.py`
- `generate_ai_agent_response.py`
- `generate_ai_decision_response.py`

如果 state 裡已經有舊版 `auto_preview_candidate.json`，且缺新欄位，記得做一次 backfill，否則 dashboard 會半新半舊。

---

## 額外真 bug（本輪抓到）

### AI confidence 降級邏輯 bug
檔案：`scripts/generate_ai_agent_response.py`

危險寫法：
```python
confidence = 'low' if confidence == 'medium' else 'medium'
```
這會把原本 `low` 誤升成 `medium`。

正確寫法：
- `high -> medium`
- `medium -> low`
- `low -> 保持 low`

---

## 最小驗證清單
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m py_compile \
  scripts/poll_order_status.py \
  scripts/filled_reconciliation.py \
  scripts/refresh_filled_reconciliation_report.py \
  scripts/generate_ai_agent_response.py \
  scripts/generate_ai_decision_response.py \
  scripts/run_auto_decision_scan.py \
  dashboard/app.py
```

Jinja 驗證：
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python - <<'PY'
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
env = Environment(loader=FileSystemLoader(str(Path('dashboard/templates'))))
env.get_template('overview.html')
print('JINJA_OK')
PY
```

Overview probe：
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python - <<'PY'
from dashboard.app import build_overview_model
m = build_overview_model()
print('data_sources' in m)
print('unreconciled_orders' in m.get('filled_reconciliation', {}))
PY
```

Dashboard 重啟：
```bash
PORT=5055
kill $(lsof -ti tcp:$PORT) || true
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
nohup .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT > dashboard.log 2>&1 &
curl -i http://localhost:5055/api/overview | head -20
```

---

## 產出物建議
完成後至少落 wiki：
- `etf-tw-dataflow-audit-p2-1.md`
- `etf-tw-order-monitor-fill-detection-p2-2.md`
- `etf-tw-decision-layer-audit-p2-3.md`

---

## 一句話原則
P2 的本質不是讓系統看起來更聰明，
而是讓它在證據不足時，少一點假裝很確定。
