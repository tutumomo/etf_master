---
name: etf-tw-state-monitoring-audit
description: ETF_TW state / dashboard / order monitoring audit workflow. Use when data layers are confused, monitoring misreports fills, or ghost orders / fallback sources need cleanup.
---

# ETF_TW State + Monitoring Audit

## 何時使用
- 使用者質疑持倉 / 掛單 / 成交敘述不可信
- 需要審計 dashboard / state / live API 的角色分工
- 需要修 `poll_order_status.py`、`filled_reconciliation.py`、dashboard source 標示
- 發現 legacy 監控腳本仍在用舊邏輯（如把 `list_trades()` 當唯一成交證據）

## 核心原則
1. live API 是優先查證層，但不是萬能真相機器
2. instance state 是 system-of-record / reconciliation 層，不是對外回答的唯一 live truth
3. dashboard 是展示與 fallback 組裝層，必須標示 source
4. local inference 可做保守推定，但不能冒充 broker 明確成交證據

## 工作流

### Phase 0：事故回溯 / 夜間異常先做 dirty diff 審計
當使用者問「昨晚你到底改了什麼」「半夜發生什麼怪事」時，不要先猜 broker 或 cron。
先做 4 件事：
- `session_search(...)` 找昨晚相關對話 / cron 摘要
- `git status --short` 看 repo 是否有未提交改動
- `git diff -- <關鍵檔>` 直接看 `dashboard/app.py`、`scripts/state_reconciliation.py`、監控腳本
- `read_file(...)` 回頭檢查 import / runtime 依賴是否自洽

重點不是只說「有改過」，而是要指出：
- 改了哪個檔
- 改了什麼功能
- 哪一行留下 runtime 風險
- 目前是否已修 / 未修 / 未提交

### Phase A：資料流審計（P2-1）
先盤點四層：
- broker live API
- instance state (`positions.json`, `orders_open.json`, `portfolio_snapshot.json`, `agent_summary.json`)
- dashboard view model (`dashboard/app.py`)
- agent 對外回答層

輸出重點：
- 哪一層是查證層
- 哪一層是落盤 / 對帳層
- 哪一層是 fallback 展示層
- 哪些地方容易被混講成單一事實

### Phase B：監控鏈 root cause 調查（P2-2）
必查：
- `scripts/poll_order_status.py`
- `scripts/filled_reconciliation.py`
- `~/.hermes/scripts/order_monitor.py`
- `scripts/adapters/base.py`
- `scripts/adapters/sinopac_adapter.py`

重點檢查：
- 是否依賴不存在的 adapter 介面（例如 `adapter.get_trades()`）
- 是否把 `list_trades()` 查不到直接解讀為失敗 / 成交
- 是否缺 broker 查證與 position delta 推定分層
- 是否仍保留 legacy order monitor 的危險邏輯

### Phase C：修正監控主鏈
`poll_order_status.py` 應改成：
1. 優先 `adapter.get_order_status(order_id)`
2. broker 查不到時，不直接下結論
3. 若有足夠 baseline + current positions 證據，再用 position delta 做保守 filled 推定
4. local inference 要標 `source_type=local_inference`，`verified=False`
5. 收盤停止條件要含盤後零股視窗

### Phase D：停用 legacy 舊腳本
若 `~/.hermes/scripts/order_monitor.py` 仍在用：
- hardcode 標的
- legacy state 路徑
- `list_trades()` 當唯一成交證據

則直接改成停用警示腳本，避免再被 cron / 人工誤用。

### Phase E：`filled_reconciliation` 升級到 order 級
舊版只有 `unreconciled_symbols` 不夠。

升級後至少要有：
- `unreconciled_orders`
- `unreconciled_order_count`
- 向後相容保留 `unreconciled_symbols` / `unreconciled_count`

每筆 order 級異常建議欄位：
- `order_id`
- `symbol`
- `status`
- `filled_quantity`
- `position_quantity`
- `issue`
- `source_type`
- `observed_at`

### Phase F：dashboard 加資料來源標示（P2-4 前置）
在 `build_overview_model()` 增加 `data_sources` 區塊，至少包含：
- positions
- orders_open
- portfolio_snapshot
- agent_summary
- filled_reconciliation

每塊至少帶：
- `source`
- `is_fallback`

## 最小驗證
```bash
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python -m py_compile \
  scripts/poll_order_status.py \
  scripts/filled_reconciliation.py \
  scripts/refresh_filled_reconciliation_report.py \
  dashboard/app.py
```

再做 2 個 smoke checks：
1. refresh 報表
```bash
.venv/bin/python scripts/refresh_filled_reconciliation_report.py
```
2. overview model 是否已吐出新欄位
```bash
.venv/bin/python - <<'PY'
from dashboard.app import build_overview_model
m = build_overview_model()
assert 'data_sources' in m
assert 'unreconciled_orders' in m['filled_reconciliation']
print('OK')
PY
```

## 常見坑
- `adapter.get_trades()` 在 base adapter 沒定義，不要假設存在
- `list_trades()` 查不到，不等於失敗或成交
- `filled_reconciliation` 若只有 symbol 級，會把多筆同標的訂單混在一起
- dashboard API 有 source label，不代表前端畫面已經顯示；若使用者要「一眼看懂」，還要補前端
- legacy `order_monitor.py` 若不直接停用，很容易被 cron 再次誤用
- 夜間/半夜異常常不是 broker 問題，而是 repo 留下未提交修改；先查 `git status` 再查 live path
- 改 datetime 正規化時，若只 `from datetime import datetime`，就不能寫 `datetime.timezone.utc`；這會變成 runtime bug。應改成 `from datetime import datetime, timezone` 後用 `timezone.utc`
- 新增 dashboard submit 路徑時，CLI / script 參數必須和目標腳本對齊；例如 `complete_trade.py` 若沒有 `--source`，dashboard 不能私自加這個 flag

## 交付物
- 一份資料流審計文件（P2-1）
- 一份監控與 fill detection 修正文檔（P2-2）
- 修好的 `poll_order_status.py`
- 停用的 legacy `order_monitor.py`
- 升級後的 `filled_reconciliation.py`
- `dashboard/app.py` 中的 `data_sources` API 欄位
