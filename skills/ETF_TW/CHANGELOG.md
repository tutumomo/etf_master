# CHANGELOG

## v1.3.6 — 2026-04-15
### Added
- **真相層級治理 (Truth Level Governance)**：正式定義三層真相分級，取代單一真相源 (SSoT) 概念。
  - Level 1: Live Direct Evidence (券商 API 即時數據)
  - Level 2: Live Unconfirmed (送單成功待驗證)
  - Level 3: Secondary Info / Snapshots (本機狀態快照)
- 更新 `docs/STATE_ARCHITECTURE.md`、`SKILL.md`、`README.md`、`INSTALL.md` 以反映此架構變更。

### Changed
- 移除所有活文件中將本機 state 稱為「唯一真相源」或「SSoT」的說法，統一改稱為「本機狀態快照」或「次級資訊」。

## v1.2.11 — 2026-04-03
### Changed
- `IMPROVEMENT_PLAN_V3.md` 已重整為主線式規劃，將後續工作改寫為：
  - Filled / Positions Reconciliation Close-the-loop
  - TW Market Calendar / Holiday Detection
  - Submit / Verification / Polling / Callback Contract Completion
  - Partial Fill / Fills Ledger / Portfolio Boundary
  - Dashboard / Summary / Docs Consolidation
- `TASKS.md` 已同步加入新版主線結構摘要，避免後續工作仍混在舊版線性項目中。

## v1.2.10 — 2026-04-03
### Changed
- dashboard overview template 現在正式顯示 filled reconciliation 區塊，並加入 OK / PENDING badge 與未對齊提示。

### Validation
- overview template / overview API / dashboard health / refresh hook / 全鏈路測試通過（78 passed）

## v1.2.9 — 2026-04-03
### Added
- 新增 `filled_reconciliation.py` 的正式 report/state IO 能力。
- 新增 `refresh_filled_reconciliation_report.py`，可由 `fills_ledger.json` + `positions.json` 生成 `filled_reconciliation.json`。
- 新增 filled reconciliation 測試：
  - `test_filled_reconciliation_report.py`
  - `test_filled_reconciliation_state_io.py`
  - `test_refresh_filled_reconciliation_report.py`
  - `test_dashboard_filled_reconciliation_health.py`

### Changed
- dashboard health warning 現可承接 filled reconciliation 警訊。
- `BROKER_RECONCILIATION_RULES.md`、`TASKS.md` 已同步 filled reconciliation / refresh hook 進度。

### Validation
- filled reconciliation / refresh hook / dashboard health / 全鏈路測試通過（76 passed）

## v1.2.8 — 2026-04-03
### Added
- 新增 `fills_ledger.py`，提供 fill facts 的最低可用 state helper 與 merge / state IO。
- 新增 fills ledger / partial fill 測試：
  - `test_fills_ledger_contract.py`
  - `test_fills_ledger_merge.py`
  - `test_fills_ledger_state_io.py`
  - `test_orders_open_callback_fills_ledger.py`
  - `test_polling_fills_ledger_sync.py`
  - `test_partial_fill_position_boundary.py`
  - `test_partial_fill_fill_ledger_contract.py`
  - `test_partial_fill_summary_boundary.py`

### Changed
- `orders_open_callback.py` 現在會在 partial fill callback 時同步更新 `fills_ledger.json`。
- `poll_order_status.py` 現在會在 partial fill polling 時同步更新 `fills_ledger.json`。
- `IMPROVEMENT_PLAN_V3.md` / `TASKS.md` 已同步 partial fill 與 fills ledger 進度。

### Validation
- partial fill / fills ledger / callback / polling / dashboard / sync 相關測試通過（67 passed）

## v1.2.7 — 2026-04-03
### Added
- 新增 `docs/BROKER_RECONCILIATION_RULES.md`，正式整理 broker reconciliation 規則：
  - status rank
  - timestamp precedence
  - broker seq precedence
  - source priority
  - partial fill quantity guard
  - metadata contract
- 新增 `test_submit_and_polling_metadata_contract.py`

### Changed
- `complete_trade.py` 新增 `build_submit_order_row()`，submit verification 寫入 `orders_open` 時帶齊 metadata。
- `poll_order_status.py` 新增 `build_polling_order_row()`，polling 寫入 `orders_open` 時帶齊 metadata。
- `IMPROVEMENT_PLAN_V3.md`、`TASKS.md` 已同步 P4-2 進度。

### Validation
- callback / polling / submit / dashboard / sync 相關測試通過（52 passed）

## v1.2.6 — 2026-04-03
### Added
- 新增 partial fill / callback precedence / stale callback 相關 edge-case 測試：
  - `test_partial_fill_edge_cases.py`
  - `test_callback_precedence_edge_cases.py`
  - `test_partial_fill_normalizer_and_stale_guard.py`

### Changed
- `order_lifecycle.py` 正式納入 `partial_filled` 狀態正規化。
- `orders_open_state.py` 新增基礎 precedence guard，避免較舊 `submitted` 狀態覆蓋較新的 partial / terminal 狀態。
- `sinopac_callback_normalizer.py` 現可帶出 `filled_quantity` / `remaining_quantity`。
- `IMPROVEMENT_PLAN_V3.md` 與 `TASKS.md` 已同步 P4 edge cases 進度。

### Validation
- partial fill / precedence / stale guard 與既有 callback / dashboard / health 測試通過（41 passed）

## v1.2.5 — 2026-04-03
### Changed
- 將 `IMPROVEMENT_PLAN_V3.md`、`TASKS.md`、`CHANGELOG.md` 同步到當前實作狀態。
- 明確標記：P1 / P2 / P3 已完成，P4 進入 callback reconciliation 主幹已建立狀態。

### Validation
- 文件同步前，callback / dashboard / intelligence / health 相關測試通過（34 passed）

## v1.2.4 — 2026-04-03
### Added
- 新增 `dashboard_health.py`，將 dashboard health / warnings / stale / intelligence readiness 聚合為單一模型。
- 新增 callback reconciliation helpers：
  - `order_event_bridge.py`
  - `orders_open_callback.py`
  - `sinopac_callback_normalizer.py`
- 新增 callback / polling / reconciliation 測試：
  - `test_sinopac_callback_normalizer.py`
  - `test_sinopac_callback_bridge.py`
  - `test_sinopac_callback_smoke.py`
  - `test_callback_polling_consistency.py`
  - `test_callback_terminal_statuses.py`
  - `test_callback_polling_verification_consistency.py`

### Changed
- `/health` API 現在回傳 reconciliation-aware health payload，不再只是固定 `{ok:true}`。
- `verify_alignment.py` 與 dashboard overview 現在都納入 state reconciliation 診斷。
- Sinopac adapter 認證成功後會預設註冊 state callback bridge，使 callback 可進入 `orders_open` 更新流程。

### Fixed
- 修正 dashboard runtime 對 `state_reconciliation` 的 import path 問題。
- 修正 `market_intelligence` / history feed 空資料導致 RSI/MACD 長時間載入中與 detail chart 404 的問題。

### Validation
- callback / polling / health / dashboard / intelligence 相關測試通過
- 當前相關測試最高累計：68 passed

## v1.2.3 — 2026-04-02
### Added
- 新增 `docs/IMPROVEMENT_PLAN_V3.md`，正式整理 live lifecycle 下一階段改造方向。
- 新增 dashboard refresh regression test，覆蓋 `/api/refresh` 成功/失敗回應契約。
- 新增 lifecycle regression tests：
  - `test_order_status_contracts.py`
  - `test_orders_open_contract.py`
  - `test_orders_open_position_boundary.py`
  - `test_submit_verification_contract.py`
  - `test_order_lifecycle_helper.py`
  - `test_poll_order_status_contract.py`

### Changed
- `complete_trade.py` 與 `poll_order_status.py` 已接入共用 `order_lifecycle.py`，統一 landed / terminal / status normalization 語意。
- dashboard `/api/refresh` 改為明確回傳 subprocess 結果，只在真失敗時回 500。

### Fixed
- 修正 5050 dashboard 仍跑舊版進程時，UI 顯示 refresh 失敗但主鏈實際已成功的問題。
- 修正 polling flow 對 `failed` / `rejected` / terminal status 的判定分散問題。

### Validation
- dashboard refresh API 測試：通過
- lifecycle / orders_open / submit verification / polling contract 測試：通過
- regression tests 累計：41 passed

## v1.2.2 — 2026-04-02
### Added
- 新增 `docs/STATE_ARCHITECTURE.md`，正式定義 ETF_TW 狀態分層、instance state 單一真相源、refresh pipeline 與 agent 對齊規則。
- 新增 `docs/SYMBOL_NORMALIZATION.md`，正式定義 canonical symbol 規範與 provider suffix（`.TW` / `.TWO`）邊界。
- 新增 symbol normalization regression tests，覆蓋 canonicalization 與 mapping 行為。

### Changed
- 將 refresh 主鏈與 decision engine 支線進一步收斂為 **instance state only**，避免 dashboard / agent / scripts 讀寫不同狀態檔。
- `refresh_monitoring_state.py` 正式納入 `market_event_context`、`market_context_taiwan`、`major_event_flag`，補齊市場上下文刷新鏈。
- `sync_market_cache.py`、`sync_ohlcv_history.py`、`sync_agent_summary.py` 已改為 canonical symbol 導向，降低 watchlist / tape / summary 的重複訊號。
- README、dashboard runbook、TASKS 已更新正式架構原則，明確要求 agent 與 ETF_TW 長期資訊對齊。

### Fixed
- 修正多支腳本仍硬寫 root `state/`，導致 instance-aware dashboard 與 agent 看到不同狀態來源的問題。
- 修正 watchlist 中 `.TW` provider symbol 進入 state，造成 `0050` / `0050.TW` 等重複訊號的問題。
- 修正 `agent_summary` 關鍵指標摘要會重複顯示 canonical 與 provider variant symbol 的問題。

### Validation
- `verify_alignment.py`：通過
- `verify_decision_engine_stability.py`：通過
- refresh 主鏈重跑：通過
- regression tests：11 passed

## v1.2.1 — 2026-03-30
### Fixed
- 正式釐清 Shioaji live 持股數量語義：**必須使用 `list_positions(..., unit=Unit.Share)`**
- 修正先前誤用 `Unit.Common` 導致 0050 / 00878 股數被讀成 0 的問題
- dashboard / state / agent 現已對齊到 `Unit.Share` 規則

### Locked Rules
- `Unit.Share` 是 live 持股數量真相源
- `Unit.Common` 不得再用於真實持股數顯示
- 若未來再出現 live 持股誤顯示為 0，視為 regression
