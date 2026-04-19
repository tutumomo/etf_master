# CHANGELOG

## v1.4.6 — 2026-04-20

### Added
- **決策自動復盤管線（Auto Decision Review Pipeline）**：完全自動化 T+N 價格回填 → verdict 判定 → 雙鏈統計 → 週報寫入 wiki 的整個循環，消除手動標記 `reviewed`/`superseded` 步驟。
  - `sync_decision_reviews.py`：每天 15:05 盤後掃描到期 T1/T3/T10 窗口，自動填入 verdict（±1.5% 門檻），三窗口填滿後自動寫入 `outcome_final`。
  - `generate_decision_quality_weekly.py`：每週六 09:05 產出 `wiki/decision-weekly-YYYY-WNN.md` 與 `wiki/decision-quality-latest.md`。
  - `provenance_logger.py`：`build_provenance_record()` 新增 `chain_sources` 參數，記錄雙鏈仲裁來源（rule_engine/ai_bridge/tier）。
  - `run_auto_decision_scan.py`：將 `consensus` dict 扁平化為 `chain_sources_payload` 傳入 provenance。
  - `decision_quality_report.json` 新增 `chain_breakdown` 區塊（rule_engine/ai_bridge/tier1_consensus/unknown_source 四桶勝率）。
- **Cron 新增 2 個 job**：`ETF 決策自動復盤`（15:05 平日）、`ETF 決策品質週報`（09:05 週六）。Job 數量 7→9。
- **verify_deployment.sh**：cron 門檻從 ≥7 更新為 ≥9。

### Validation
- 15 新增測試全通：`test_sync_decision_reviews.py`（10 tests）、`test_generate_decision_quality_weekly.py`（5 tests）
- 全套 364 tests passed，4 個既有失敗不變

## v1.4.5 — 2026-04-19

### Added
- **Wiki 投資策略知識注入決策鏈**：`generate_ai_decision_request.py` 新增 `wiki_context.investment_strategies` 與 `wiki_context.undervalued_ranking`，使 dashboard 建議決策能引用「投資策略十大實務」與「ETF 低估排行」知識。
- **Wiki 知識庫新增 4 頁**：`skills/ETF_TW/wiki/investment-strategies.md`（十大策略+5陷阱+0407 Self-Check）、`undervalued-etf-ranking.md`（TOP10 低估排行）、`market-view.md`（風險升級）、`risk-signal.md`。
- **P0 修復 market_value=0**：`sync_live_state.py` 在 Shioaji API 回傳 market_value=0 時，改從 positions 計算，total_equity 同步重算。

### Validation
- `generate_ai_decision_request.py` 產出 `wiki_context` 含 4 個非空欄位：`market_view`(1917字元)、`risk_signal`(2329字元)、`investment_strategies`(5184字元)、`undervalued_ranking`(2270字元)。

## v1.4.4 — 2026-04-19

### Fixed
- **Wiki 背景鏈路修補（request 層）**：`generate_ai_decision_request.py` 改為自動解析 profile wiki (`~/.hermes/profiles/etf_master/wiki`) + instance wiki fallback，不再依賴錯誤路徑 `docs/wiki/shioaji`。
- **Wiki 實體檔名對齊**：支援 `{symbol}.md` 與 slug 形式（如 `0050-yuanta-taiwan-50.md`），持倉標的可正確注入 `wiki_context.entities`。
- **Wiki 風險概念注入**：新增 `wiki_context.risk_signal`，與 `market_view` 一起提供給後續推理鏈。
- **智能體推理層接線**：`generate_ai_agent_response.py` 新增 wiki fallback 載入，並把 worldmonitor 指標（供應鏈/地緣/台海/告警）明確併入 `risk_context_summary`，避免「request 有資料、reasoning 沒使用」。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/generate_ai_decision_request.py`：`wiki_context.market_view/risk_signal/entities` 皆非空。
- `AGENT_ID=etf_master .venv/bin/python3 scripts/generate_ai_agent_response.py`：`candidate.reason` 出現 Wiki 分類；`reasoning.risk_context_summary` 含 worldmonitor 欄位。
- `pytest tests/test_ai_decision_bridge_contract.py -q`：3 passed
- `pytest tests/test_sync_worldmonitor.py -q`：9 passed

## v1.4.3 — 2026-04-19

### Added
- **GitHub 操作可追溯補強**：新增 `RELEASE_AUDIT.md`，固定記錄 `tag -> commit -> scope -> validation`。
- **Commit scope guard**：新增 `.github/workflows/commit-scope-guard.yml`，當 commit message 為 `docs(...)` 或 `docs:` 時，禁止夾帶非文件路徑。
- **Local hook guard**：新增 `.githooks/commit-msg`（可搭配 `git config core.hooksPath .githooks`）在本機預先阻擋 `docs` 混合 commit。
- **Release tag audit**：新增 `v1.4.0-audit` annotated tag（對齊 `v1.4.0` 指向 commit），提升版本審計可讀性。

## v1.4.2 — 2026-04-19

### Fixed
- **審計口徑對齊（worldmonitor jobs 路徑）**：統一明確為 repo root 的 `cron/jobs.json`；`skills/ETF_TW/cron/jobs.json` 為錯誤路徑，不再使用。
- **審計口徑對齊（commit 性質）**：釐清 `d7ac4c4` 雖採 `docs(v1.4.0)` 命名，但實際為 **文件 + 功能 + 測試 + wiki** 的混合提交（22 files changed），後續審計與回報以實際 diff 為準。

## v1.4.1 — 2026-04-19

### Fixed
- **Preview/Validate/Submit-Preview 風控鏈一致化**：`scripts/etf_tw.py` 的 `preview-account`、`validate-account`、`submit-preview` 全部接入 `evaluate_pre_flight_gate()`，統一使用 live account context（cash/positions）走 `pre_flight_gate.check_order()`。
- **validate-account 真偽差異修補**：不再只看 adapter `validate_order()`；現在 `valid` 需同時滿足 `validate_order && pre_flight_gate.passed`，並輸出 `pre_flight_gate` 詳細阻擋原因。
- **submit-preview 最終檢核補強**：`validation.valid` 併入 gate 結果，若 gate 阻擋會寫入 `validation.errors`，避免「可預覽但風控已拒絕」的假陽性。
- **Bug 2 修復驗證入冊**：確認 `scripts/distill_to_wiki.py --help` 僅顯示說明，不再觸發 wiki 寫入。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py preview-account --account sinopac_01 data/tmp_preview_risk_test.json` → `status=blocked_by_gate`（原因：`outside_trading_hours`，表示已成功走 gate）
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py validate-account --account sinopac_01 data/tmp_preview_risk_test.json` → `valid=false`，含 `pre_flight_gate` 與阻擋理由
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py submit-preview --account sinopac_01 data/tmp_preview_risk_test.json` → `validation.valid=false`，`errors` 含 gate 阻擋訊息
- `AGENT_ID=etf_master .venv/bin/python3 -c "from scripts.pre_flight_gate import check_order; ... force_trading_hours=False ..."` → `reason=exceeds_sizing_limit`, `allowed=169`
- `before/after stat + .venv/bin/python3 scripts/distill_to_wiki.py --help` → wiki mtime 不變（未寫入）
- `AGENT_ID=etf_master .venv/bin/python3 -m pytest tests -q` → **353 passed**

## v1.4.0 — 2026-04-19

### Added
- **worldmonitor 全球風險雷達整合**：新增 `sync_worldmonitor.py`（daily/watch 雙模式）、`worldmonitor_snapshot.json`、`worldmonitor_alerts.jsonl`、dashboard `/api/worldmonitor-status` 與 `/api/worldmonitor/refresh`。
- **AI 決策輸入擴充**：`inputs.worldmonitor_context` 正式納入 `ai_decision_request.json`，作為第 14 個輸入源。

### Fixed
- 修正 `sync_worldmonitor.py` 在 watch 模式 L3 事件觸發時的錯誤路徑（`skills/ETF_TW/skills/ETF_TW/...`），確保 `check_major_event_trigger.py` 能正確被呼叫。
- 修正 worldmonitor 輸入源描述不一致（第 13/14 個輸入源）為「第 14 個輸入源」。
- 修正每日送單配額測試使用硬編碼日期造成的失敗（改為 Asia/Taipei 當日動態日期），恢復全套測試穩定性。

### Validation
- `tests/test_sync_worldmonitor.py`: 9 passed
- `pytest tests/ -q`: 全綠（修復前 3 failed）

### Maintenance
- 測試警告清零：`tests/test_venv_executor.py` 移除 `return bool` 反模式，新增 `pytest.ini` 過濾第三方 `pydantic` 相容性警告，完整測試輸出 0 warnings。

## v1.3.2 — 2026-04-19

### Added
- **Hermes multi-instance 契約落地**：文件全面補齊 `AGENT_ID` 顯式注入規範，將新安裝預設從「依賴 fallback」改為「入口明確指定 instance」。
- **新裝流程補強**：`README.md`、`INSTALL.md`、`BOOT.md` 新增 AGENT_ID 設定與範例，明確標記 `OPENCLAW_AGENT_NAME` 為 legacy fallback。

### Changed
- `scripts/start_dashboard.sh`：啟動時自動注入 `AGENT_ID=${AGENT_ID:-etf_master}`，並同步填入 legacy 變數給舊腳本相容。
- `scripts/etf_core/context.py`：instance 解析改為 `AGENT_ID` 優先、`OPENCLAW_AGENT_NAME` 次之；缺失警告改為可直接執行的修復導引。
- `scripts/sync_news_via_opencli.py` / `scripts/sync_news_from_local.py`：示例與 state 路徑解析改為 AGENT_ID 優先。

### Validation
- `AGENT_ID=etf_master .venv/bin/python3 scripts/etf_tw.py search 0050`：exit code 0，且不再出現 defaulting 警告。
- `.venv/bin/python3 scripts/distill_to_wiki.py --help`：exit code 0（確認既有修復未回歸）。

## v1.2.2 — 2026-04-17

### Added
- **決策品質報告**：新增 `decision_quality_report.json` 生成流程，統計策略對齊率、confidence bucket 分佈、保險絲攔截率與 Tier arbitration 結果。
- **Paper 壓力測試**：新增多輪掃描與幽靈委託檢測流程，產出 `paper_stress_test_report.json`，驗證 paper mode 週期穩定性。
- **決策回測框架**：新增 `backtest_decision_outcomes.py`，從 `ai_decision_outcome.jsonl` 計算 PnL、勝率、最大回撤與 `quality_gate_passed`。
- **Live Submit SOP**：修正永豐金 `ordno` 讀取路徑，新增 `verify_order_landed()` 3 次輪詢 ghost detection，並建立 `live_submit_sop.py` 單一授權下單入口。
- **Dashboard Live 授權閘門**：新增 `/api/live-mode/status`、`/api/live-mode/unlock` 與 overview 解鎖卡片，雙重確認字串與品質閘門在伺服器端強制驗證。
- **Live submit 回歸測試**：新增 7 場景 regression suite，覆蓋 happy path、ghost、gate block、adapter exception、double-submit dedup、live mode lock。

### Validation
- 全套測試：**328 passed, 6 warnings**

## v1.2.1 — 2026-04-17

### Added
- **Phase 6 決策對齊**：Rule Engine 新增 `OVERLAY_MODIFIERS`（情境覆蓋加分/懲罰）、`BUY_THRESHOLD_BY_RISK`（動態買入門檻）、`strategy_aligned` 候選欄位。
- **AI Bridge 策略強化**：`STRATEGY_GROUP_BONUS` 依 `base_strategy` 動態調整 AI 評分，候選結果帶 `strategy_aligned` 旗標。
- **仲裁優化**：`_adjust_confidence()` 雙鏈同向時升級信心等級，任一鏈失對齊時降級；`resolve_consensus()` 回傳 `strategy_alignment_signal`。
- **LLM-Wiki 注入**：AI Bridge 對前 3 名候選自動讀取本地 `llm-wiki/etf/{sym}.md` 知識注入 Prompt。
- **Phase 8 一鍵全同步**：新增 `_run_full_pipeline_helper()` 與 `/api/decision/full-pipeline` 整合端點；Dashboard 加入一鍵同步按鈕，精簡冗餘操作。
- **Phase 9 Safety Redlines**：Dashboard「交易閾值與安全紅線」UI 區塊落地，支援金額/股數/集中度/日虧損/AI 信心全參數設定與持久化；`pre_flight_gate.py` 全面改寫為 fail-fast 優先序架構，7 道檢查點各有 machine-readable reason code。
- **Dashboard 操作按鈕補齊**：規則引擎「立即規則掃描」、AI Bridge「更新背景知識」/「生成 AI 建議」/「重跑決策管線」。
- **預設券商修復**：`_get_default_broker()` 從帳戶別名推導，解決 N/A 顯示問題。
- **全域 Banner 文字補齊**：`overview.html` 加入技術指標缺失與未對齊成交的精確提示文字。

### Fixed
- `test_safety_redlines.py`：修正錯誤 import 路徑、`@patch` 目標、過時 reason code、sizing context 干擾。
- `test_fuse_v1` / `test_trade_validation` / `test_sizing_policy` / `test_ui_flow`：補齊 `_skip_safety_redlines` context flag，解除 state 檔案對測試環境的干擾。
- `test_dashboard_global_banner_*`：補齊 overview.html 精確 banner 字串。

### Validation
- 全套測試：**275 passed, 0 failures**

---

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
