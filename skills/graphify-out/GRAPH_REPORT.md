# Graph Report - /Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW  (2026-04-14)

## Corpus Check
- Large corpus: 341 files · ~96,691 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 2654 nodes · 3164 edges · 528 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 784 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Order` - 90 edges
2. `BaseAdapter` - 86 edges
3. `Position` - 59 edges
4. `AccountBalance` - 59 edges
5. `[H3] 帳號密碼登入` - 45 edges
6. `AccountManager` - 40 edges
7. `SinopacAdapter` - 35 edges
8. `main()` - 30 edges
9. `CathayAdapter` - 29 edges
10. `PaperAdapter` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Manages multiple trading accounts across different brokers.          Features:` --uses--> `BaseAdapter`  [INFERRED]
  ETF_TW/scripts/account_manager.py → ETF_TW/scripts/adapters/base.py
- `Initialize account manager.                  Args:             config_path: Path` --uses--> `BaseAdapter`  [INFERRED]
  ETF_TW/scripts/account_manager.py → ETF_TW/scripts/adapters/base.py
- `Find configuration file, prioritizing instance-specific config.` --uses--> `BaseAdapter`  [INFERRED]
  ETF_TW/scripts/account_manager.py → ETF_TW/scripts/adapters/base.py
- `Load configuration from file.` --uses--> `BaseAdapter`  [INFERRED]
  ETF_TW/scripts/account_manager.py → ETF_TW/scripts/adapters/base.py
- `Load broker registry.` --uses--> `BaseAdapter`  [INFERRED]
  ETF_TW/scripts/account_manager.py → ETF_TW/scripts/adapters/base.py

## Hyperedges (group relationships)
- **Theme: etf_ecosystem** — etf_00679b, etf_00878 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00923, etf_00679b, etf_00878, etf_00929, etf_00892 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00713, etf_00637l, etf_00679b, etf_00881, etf_00878 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00679b, etf_00878 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00679b, etf_00878, etf_00922 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00679b, etf_00878, etf_00929 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00679b, etf_00878 [INFERRED 0.70]
- **Theme: etf_ecosystem** — etf_00679b, etf_00878 [INFERRED 0.70]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (74): AccountBalance, BaseAdapter, MarketDataProvider, Position, Abstract base class for all broker adapters., Default empty implementation for order history., Represents an order (preview, paper, or live)., Represents a position in an account. (+66 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (99): AccountManager, get_account_manager(), Get account configuration by alias.                  Args:             alias: Ac, Get adapter for an account.                  Args:             alias: Account al, Authenticate an account.                  Args:             alias: Account alias, Save current configuration to file., Set the default account alias., Get the full configuration. (+91 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (118): [DOC] shioaji_api_reference, [H2] 目錄, [H1] 預設股票帳號, [H1] 1. 初始化, [H1] 10. 登出, [H1] 2. 登入, [H1] 3. 送單, [H1] 4. 取得商品檔 (+110 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (59): build_submit_order_row(), execute_trade(), load_orders_open(), main(), Execute a complete trade with risk control and logging.      Args:         symbo, save_orders_open(), build_fill_fact_row(), build_fills_ledger_payload() (+51 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (71): add_watchlist_symbol(), ai_decision_generate(), ai_decision_refresh_background(), ai_decision_rerun(), AIDecisionOutcomeRequest, AIDecisionReviewRequest, auto_trade_submit(), AutoTradeConfigRequest (+63 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (45): [DOC] SKILL, [H2] 技能描述, [H2] 核心能力, [H2] 與 OpenClaw Agent 的整合, [H3] 適合使用此技能, [H3] 2. 決策輔助模式（需確認後執行）, [H3] 決策鏈重檢機制（2026-04-13 實作）, [H3] 3. 執行模式（嚴格限制） (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (35): [DOC] AI_DECISION_BRIDGE, [H2] 目的, [H2] 核心定位, [H3] 建議欄位, [H3] AI Decision Bridge 初期權限, [H4] 目的, [H3] 1. AI 不在線, [H3] 1. `ai_decision_request.json` (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (30): _add_provenance_reflection_tag(), _append_jsonl(), _load_json(), _load_jsonl_last_matching(), Tag provenance record with reflection info., record_reflection(), _append_jsonl(), _determine_review_window() (+22 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (33): [DOC] README, [H2] 🌟 核心功能, [H2] ⚖️ 交易核心鐵律, [H3] 已驗證落地（可審核）, [H3] 1. 更新技能包, [H3] 1. 安裝 Python 套件, [H3] 2. 初始化資料庫, [H3] 2. 執行對齊工具 (Setup Tool) (+25 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (23): build_agent_consumed_response_payload(), build_ai_decision_request(), build_ai_decision_request_from_state(), build_ai_decision_response(), _now_iso(), decide_action(), _is_duplicate_session(), _load_market_intelligence() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (11): ABC, BaseBroker, Base Broker Interface for ETF_TW Pro, BaseBroker, get_broker_manager(), Broker Factory to manage multiple broker instances, Add a broker instance to the manager, CathayBroker (+3 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (26): [DOC] rshioaji-upgrade-path, [H3] 官方 / 上游來源, [H3] 觀察到的重點, [H3] 規則 1：先分清楚「可用」與「已驗證可正式採用」, [H3] 規則 2：本地成功 ≠ 官方測試通過, [H3] 規則 4：事件驅動先用在觀察層, [H2] 1. 這份文件要解決什麼問題, [H2] 2. 已確認的主要來源 (+18 more)

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (25): [DOC] STATE_ARCHITECTURE, [H2] 目的, [H2] 核心原則, [H3] 檔案, [H3] 1. Instance state 是唯一正式真相源, [H3] 1. 策略抬頭對齊（Single Source of Truth）, [H3] 2. 模式對齊, [H3] 2. Root state 僅視為 legacy / migration residue (+17 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (15): get_risk_controller(), Check for duplicate orders., Reset daily stats if date changed., Record order for duplicate checking and statistics., Get daily trading summary., Check if any circuit breakers are triggered.                  Returns:, Risk limit configuration., Get or create the global risk controller. (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (17): build_live_account_snapshot(), build_live_positions_payload(), main(), # NOTE: shioaji may spawn background threads; in some environments Python finali, should_sync_live_state(), load_json(), main(), build_account_snapshot() (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (10): ETF_TW_Pro, ETF_TW Pro - 主服務模組 整合報價、情報、模擬盤功能與真實券商 API，提供統一入口, 初始化服務         :param use_real_broker: 是否使用真實券商 API (False 則使用本地 SQLite 模擬盤), buy_etf(), get_simulator_status(), ETF_TW Pro - 模擬盤交易模組 提供虛擬資金進行模擬交易，驗證策略, 模擬賣出 ETF     回傳：(成功與否, 訊息，交易詳情), 取得模擬盤狀態     包含：現金、持倉、總資產、損益 (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (23): [DOC] TASKS, [H2] 已完成的任務, [H2] 任務狀態圖例, [H3] 0. State Architecture 收斂（NEW）, [H3] 1. Paper Ledger Initialization, [H3] 2026-03-23, [H3] 2. Broker Adapter 實作, [H3] 3. 風控規則強化 (+15 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (7): _append_jsonl(), build_registration_records(), write_registration_records(), cron_add_job(), cron_list_payload(), Return cron list payload.      Note: openclaw may return either a list or a dict, Add cron job via CLI.      Prefer CLI JSON mode if available, else fall back to

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (22): [DOC] CHANGELOG, [H3] Added, [H3] Changed, [H3] Fixed, [H3] Validation, [H3] Added, [H3] Changed, [H1] CHANGELOG (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (22): [DOC] phase4-implementation, [H2] 完成日期, [H2] 完成項目, [H3] 1. 抽象基類優先, [H3] 2. 工廠模式, [H3] 3. 非同步設計, [H3] 4. 配置與代碼分離, [H3] 5. 向後相容 (+14 more)

### Community 20 - "Community 20"
Cohesion: 0.13
Nodes (11): auto_reflect_if_ready(), _load_json(), _append_jsonl(), _load_json(), record_outcome(), _load_json(), Write a canonical review artifact for dashboard/agents to consume., run_auto_post_review_cycle() (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (20): get_broker_config(), get_instance_config(), get_instance_dir(), get_instance_id(), get_log_dir(), get_port(), get_private_dir(), get_runtime_dir() (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (21): [DOC] INSTALL, [H2] 快速安裝, [H1] 建立虛擬環境, [H2] 目錄結構說明, [H3] 方法一：直接使用（推薦）, [H3] 1. 建立模擬帳戶初始資金, [H3] 1. 透過 OpenClaw Agent 使用, [H3] 2. 建立初始持倉（可選） (+13 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (21): [DOC] fix-summary-P1-P5, [H2] 問題根源分析, [H1] 或執行其他腳本, [H2] 修復內容, [H3] 現有架構 (不變), [H1] 1. 確認在交易時段, [H1] 2. 執行狀態對帳, [H1] 3. 正式送單 (+13 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (20): [DOC] SINOPAC_REVIEW_REPORT_2026-03-26, [H2] 基本資訊, [H2] 一、複查結論, [H3] 結論, [H3] 1. 正式帳務查詢, [H3] 3. 成交回報回調, [H3] 4. 訂單狀態查詢, [H3] 5. 取消委託 (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.18
Nodes (18): backfill_journals(), build_daily_journal(), _determine_outcome(), _extract_fill_summary(), _extract_order_summary(), _extract_positions_summary(), list_journals(), load_journal() (+10 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (18): append_skip_reason(), build_candidate_symbols(), build_empty_intelligence_warning(), build_market_intelligence_payload(), calc_bbands(), calc_macd(), calc_momentum(), calc_rsi() (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (19): [DOC] beginner-guide, [H3] 優點, [H2] 新手常見錯誤, [H2] 什麼是 ETF？, [H3] 手續費, [H3] 1. 只看配息率, [H3] 2. 頻繁交易, [H3] 3. 轉入資金 (+11 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (18): [DOC] MANIFEST, [H2] 統計摘要, [H1] 應輸出：15+, [H1] 應輸出：5+, [H2] 目錄結構總覽, [H2] 主要文件 (5 個), [H2] 參考文件 (15+ 個), [H3] 主腳本 (16 個) (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (18): [DOC] phase5-sinopac-scaffold, [H2] 完成日期, [H1] 使用永豐金帳戶進行模擬交易, [H2] 完成項目, [H3] 認證流程, [H3] 1. 取得永豐金 API 憑證, [H3] 1. 永豐金證券適配器 (`scripts/adapters/sinopac_adapter.py`), [H3] 2. 工廠模式整合 (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (17): [DOC] SINOPAJI_AI_ASSISTANT_COMPARISON, [H2] 報告基本資訊, [H2] 執行摘要, [H3] 立即改善 (本週內), [H3] 中期改善 (1 個月), [H3] 1. 登入與認證 (100%), [H3] 短期改善 (1-2 週), [H3] 2. 合約查詢 (100%) (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (17): [DOC] phase6-complete, [H2] 完成日期, [H1] 初始化, [H2] 完成項目, [H2] Phase 6 總結, [H3] 完整交易流程（含風控與審計）, [H3] 1. 查詢交易日誌, [H3] 2. 風險控制檢查 (+9 more)

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (17): [DOC] risk-controls, [H1] 風控規則詳解, [H2] 核心原則, [H3] 三不原則, [H3] 1. 市場風險, [H3] 2. 部位風險, [H3] 3. 資料風險, [H3] 4. 單位風險 (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (17): [DOC] LAYERED_REVIEW_CRON_STANDARD, [H2] 目的, [H2] 標準流程, [H3] 驗證方式, [H4] 正確做法（推薦）, [H3] 🚫 跨平台路徑硬編碼禁令（CRITICAL）, [H3] 實際建立的 cron jobs（etf_master）, [H2] dedupe_key 標準 (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.19
Nodes (15): backfill_return_pct(), dedup_decisions(), fetch_price_at_date(), fetch_price_n_days_later(), main(), parse_date(), Get closing price for symbol on target_date., Get closing price N trading days after decision_date. (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (16): [DOC] trading-workflow, [H1] 交易流程說明, [H2] 核心流程, [H3] 預設回報格式, [H3] 1. 單位混淆, [H3] 1. Validate（驗證）, [H3] 2. 大額交易, [H2] 當前持倉摘要（截至 2026-03-17 23:49） (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (16): [DOC] sinopac-onboarding-public, [H2] 目的, [H2] 核心結論, [H3] 錯誤觀念, [H3] 1. `Account Not Acceptable.`, [H3] 2. `Please activate ca for person_id: ...`, [H3] 3. `該股票已收盤`, [H3] 4. 本地模擬成功，但官方看不到模擬單 (+8 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (16): [DOC] live-trading-sop, [H2] 整股差異, [H1] broker_order_id 為 null = 幽靈單，禁止輸出「✅ 已正式掛單」, [H2] 委託驗證表, [H1] 確認：broker_order_id 非 null, [H2] 下單流程（盤中零股 — ETF 最常用）, [H1] Live 交易 SOP（標準作業程序）, [H1] 確認：ordno 非空 (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (16): [H2] 常用常數速查, [H2] 22. 已知問題, [H1] Action, [H3] ai.sinotrade.com.tw 403 Forbidden, [H3] api.logout() Segfault, [H3] CA 憑證路徑, [H3] github.io DNS 解析（IPv6）, [H1] OrderType (+8 more)

### Community 39 - "Community 39"
Cohesion: 0.2
Nodes (15): [DOC] FINAL_SUMMARY, [H2] 📋 專案資訊, [H1] 搜尋, [H2] 🎯 專案目標, [H3] 核心程式碼, [H3] 1. 多券商適配器, [H3] 2. 風險控制, [H3] 3. 審計追蹤 (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (15): [DOC] api-integration, [H3] Account registry, [H3] Adapter base interface, [H1] API Integration, [H2] Architecture, [H3] Broker registry, [H2] Config expectations, [H2] Goal (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.17
Nodes (15): [DOC] IMPROVEMENT_PLAN_V3, [H2] 目的, [H2] 這兩天已完成的核心成果, [H3] 目標, [H3] 1. Orders Open / Broker Reconciliation 主幹已建立, [H3] 2. Partial Fill 鏈已從概念走到可用骨架, [H3] 3. Filled Reconciliation 鏈已成形, [H3] 4. Dashboard / State / Warning 顯示層明顯強化 (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.21
Nodes (13): _compute_group_trends(), _compute_macd_breadth(), _compute_rsi_distribution(), _compute_sma_structure(), _compute_volatility(), _determine_regime_from_signals(), main(), SMA alignment: how many ETFs in bull/bear alignment. (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (14): [DOC] SINOPAC_API_TEST_REPORT, [H2] 測試基本資訊, [H2] 測試目的, [H3] 目前限制, [H3] 2. 審核通過後測試, [H3] 3. 功能整合, [H3] 1. 提交測試結果給永豐, [H3] 1. API 登入測試 (+6 more)

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (14): [DOC] BROKER_RECONCILIATION_RULES, [H2] 目的, [H2] 真相源與責任分界, [H3] 規則, [H1] Broker Reconciliation Rules, [H2] 券商序號優先序（Broker Sequence Precedence）, [H3] callback / normalizer row, [H2] Metadata Contract (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.19
Nodes (14): [DOC] SYMBOL_NORMALIZATION, [H2] 目的, [H2] 核心原則, [H3] 第一波, [H3] 1. State 層只允許 canonical symbol, [H3] 2. Provider symbol 只在外部取價層使用, [H3] 3. watchlist / positions / orders / portfolio / summary 一律使用 canonical symbol, [H3] 4. market_cache 可保留 provider 嘗試資訊，但 quotes key 應以 canonical symbol 為準 (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (14): [DOC] AI_RESEARCH_METHOD, [H2] 目的, [H2] 核心原則, [H3] 1. 固定可比較迭代, [H3] 2. 固定 quality metric, [H3] 3. Policy-driven 進化, [H3] 4. 小步可回滾, [H3] 5. 自動研究、自動復盤，但執行授權分離 (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.23
Nodes (13): [DOC] ENHANCED_FEATURES_GUIDE, [H3] 功能說明, [H1] 建立適配器, [H2] 完整範例, [H3] 使用方式, [H3] 1. 檢查極端價格, [H3] 2. 批量驗證, [H2] ✅ 功能 1：漲跌停檢查 (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.19
Nodes (13): [DOC] OPTIMIZATION_LOG, [H2] 優化日期, [H1] ✅ 無警告，直接預覽, [H2] 優化目標, [H3] 一般交易（無干擾）, [H3] 1. 簡化風控提醒 ✅, [H1] ⚠️ 大額交易提醒：下單數量 15,000 股 (15 張)，請確認是否為預期數量。, [H1] 測試 1: 正常小額交易 (100 股) (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.19
Nodes (13): [DOC] architecture_review_20260409, [H2] 📊 審查背景, [H2] ✅ 目前架構的優勢, [H3] 已做對的事情, [H3] 缺口 1：實質的自進化機制, [H3] 缺口 2：更強的風險控制, [H3] 缺口 3：真正的自主運行, [H3] 1. 「自主判斷」的定義問題 (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.15
Nodes (13): [DOC] AI_DECISION_STATUS, [H1] AI Decision Status (Handoff / Roadmap), [H2] Canonical docs to read first, [H2] Canonical scripts (entry points), [H2] Canonical state rules (non-negotiable), [H3] Completed, [H2] Current status (as of 2026-04-03), [H3] In progress / remaining (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.24
Nodes (10): build_order_state_machine(), load_json(), main(), P3: 建立訂單狀態機      狀態轉換:     pending → submitted → [filled | cancelled | rejected], P3: 驗證 orders_open 狀態      檢查：     1. 所有訂單的狀態是否合法     2. 終端狀態的訂單是否已正確清理, P3: 執行完整狀態對帳      返回：     - 對帳結果     - 發現的問題     - 建議行動, P3: 對帳 orders_open 與 positions      檢查：     1. orders_open 中的 filled 訂單是否在 posit, reconcile_orders_with_positions() (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.24
Nodes (11): _compute_defensive_bias(), _compute_market_breadth(), _detect_active_events(), _determine_regime(), _generate_summary(), main(), Determine event regime from breadth data.      Returns: (event_regime, global_ri, Determine defensive bias from breadth + regime. (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.21
Nodes (10): calculate_technical_indicators(), get_historical_data(), get_price_change(), get_stock_info(), ETF_TW Pro - 報價模組 串接 Yahoo Finance 取得即時與歷史股價, 取得股價漲跌幅     period: 1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, 取得股票/ETF 基本資訊     symbol: 代號 (如：0050.TW, 006208.TW), 取得歷史股價資料     period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (12): [DOC] GEMINI, [H3] Dashboard, [H2] Development Conventions, [H2] Directory Structure Highlights, [H1] ETF_TW: Taiwan ETF Investing Assistant, [H2] Getting Started, [H3] Installation, [H2] Key Commands (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (12): [DOC] sinopac-troubleshooting-public, [H2] 目的, [H2] 最後提醒, [H3] 症狀, [H2] 1. 官方看不到模擬測試紀錄, [H2] 2. `Account Not Acceptable.`, [H2] 3. `Please activate ca for person_id: ...`, [H2] 4. `該股票已收盤` (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.24
Nodes (12): [DOC] test_report_20260304, [H2] 📊 測試結果總覽, [H2] 🔍 詳細測試數據, [H3] 測試覆蓋率, [H3] 問題 1：技術指標計算異常, [H3] 1. 報價模組測試, [H3] 2. 情報爬蟲測試, [H3] 問題 2：股價漲跌顯示為 0.00% (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.25
Nodes (10): _estimate_market_breadth(), _estimate_taiex_trend(), _estimate_vix_proxy(), Estimate VIX proxy from annualized volatility of ETF prices., Estimate market breadth from watchlist quote changes., Main sync function. Returns the written payload., Try to get TAIEX data via shioaji., Estimate TAIEX trend from ETF intelligence (proxy). (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (10): _build_llm_prompt(), _call_llm(), generate_llm_event_context(), _parse_llm_response(), Try to call an LLM API. Returns response text or None.          Strategy order:, Parse LLM JSON response. Tolerant of markdown fences., Validate and normalize LLM output fields., Main entry: try LLM, fallback to rule engine. (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.24
Nodes (6): build_decision_memory_context(), _read_jsonl(), build_ai_decision_quality_payload(), write_ai_decision_quality_state(), build_quality_hooks(), _read_jsonl()

### Community 60 - "Community 60"
Cohesion: 0.4
Nodes (10): build_candidate_symbols(), build_quote_entry(), canonicalize_symbol(), ensure_watchlist_integrity(), fetch_price(), get_config_watchlist(), load_symbol_mappings(), main() (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (1): ETF_TW Pro - 資料庫模組 負責 SQLite 資料庫的初始化與操作

### Community 62 - "Community 62"
Cohesion: 0.22
Nodes (11): [DOC] phase4-complete, [H2] 🎉 完成狀態, [H2] ✅ 完成清單, [H3] 核心架構, [H3] 1. 列出所有券商, [H3] 2. 列出所有帳戶, [H3] 3. 使用特定帳戶進行模擬交易, [H3] 4. 執行完整測試 (+3 more)

### Community 63 - "Community 63"
Cohesion: 0.22
Nodes (11): [DOC] roadmap, [H2] 版本歷史, [H2] 貢獻指南, [H3] 優先級：高, [H1] ETF_TW 發展路線圖, [H3] 版本格式：MAJOR.MINOR.PATCH, [H2] 當前待辦（TASKS.md）, [H3] v1.0（2026-03-23）- 初始版本 (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.2
Nodes (11): [DOC] plugin-readiness-assessment, [H2] 安全與可移植性問題, [H2] 補強優先級, [H3] 已有 ✅, [H3] 還缺 ❌（65%）, [H2] 自主下單交易完成度：35%, [H2] 整體完成度：65%, [H1] ETF_TW Plugin Readiness Assessment (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (11): [DOC] AI_AGENT_RESPONSE_LIFECYCLE, [H2] 目的, [H2] 最小生命週期, [H2] Agent-Consumed Response 最小欄位, [H1] AI Agent Response Lifecycle, [H2] Source 分層, [H3] `source = "ai_agent"`, [H3] `source = "ai_decision_bridge"` (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.27
Nodes (5): build_reconciliation_report(), collect_unreconciled_filled_symbols(), load_json(), main(), refresh_reconciliation_report()

### Community 67 - "Community 67"
Cohesion: 0.29
Nodes (9): _build_llm_prompt(), _build_rule_based_reasoning(), _call_llm(), generate_llm_decision_reasoning(), _parse_json_response(), Build prompt for LLM to generate political-economic reasoning., Call LLM via ollama HTTP API → cloud API → ollama CLI fallback.          Strateg, Parse JSON from LLM response. (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.2
Nodes (2): BrokerAdapterExample, Example contract only. Live trading is not implemented in this version.

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (9): check_port(), find_available_port(), link_agent_tools(), list_agents(), main(), Create symlinks for agent-specific tools (Standard OpenClaw Setup)., Check if a port is in use., Scan for the next available port. (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.27
Nodes (10): [DOC] data-sources, [H1] 資料來源與更新規則, [H2] 資料來源, [H3] 即時資料（盤中）, [H3] 1. 股價資料, [H3] 2. 技術指標, [H3] 3. 新聞情報, [H3] 4. ETF 基本資料 (+2 more)

### Community 71 - "Community 71"
Cohesion: 0.22
Nodes (4): 測試 venv_executor.py 腳本, 測試 state_reconciliation_enhanced.py 腳本, test_state_reconciliation_script(), test_venv_executor_script()

### Community 72 - "Community 72"
Cohesion: 0.44
Nodes (8): build_portfolio_brief(), build_risk_brief(), build_strategy_header(), build_tape_brief(), build_watchlist_brief(), canonicalize_symbol(), load(), main()

### Community 73 - "Community 73"
Cohesion: 0.22
Nodes (9): [DOC] broker-onboarding, [H2] After account opening, [H1] Broker Onboarding, [H2] Core account concepts in Taiwan, [H2] Documents to prepare, [H3] Securities account, [H3] Settlement account, [H2] Typical opening flow (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.25
Nodes (9): [DOC] market-view, [H2] 當前體制判定, [H2] 策略框架, [H3] 悲觀情境（15%）, [H2] 短期預判（1-5日）, [H2] 盤中關鍵數據（2026-04-14 10:31）, [H3] 樂觀情境（40%）, [H3] 中性情境（45%） (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.32
Nodes (5): DummyContract, DummyInnerOrder, DummyPartialStatus, DummyTrade, test_normalize_sinopac_partial_fill_keeps_fill_metadata()

### Community 76 - "Community 76"
Cohesion: 0.36
Nodes (7): _parse_rss_feed(), Fetch and parse an RSS feed., Apply keyword-based tagging., Simple keyword sentiment: bullish/bearish/neutral., _sentiment_headline(), sync_news(), _tag_headline()

### Community 77 - "Community 77"
Cohesion: 0.39
Nodes (7): main(), _open_and_extract(), Tag article with keywords, category, and sentiment bias., Run opencli browser command and return stdout., Open a page, wait, then extract articles via JS eval.          Uses shell chaini, _run_opencli(), _tag_article()

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (7): patch(), _patched_getaddrinfo(), dns_fix.py — 沙盒 DNS 應急備案模組 ======================================  ## 背景  Hermes, Replacement getaddrinfo: 系統 DNS 失敗時才走 UDP DNS。, 測試系統 DNS，若正常則直接返回（零幹擾）。     若系統 DNS 損壞，套用 monkey-patch 並回報。, Raw UDP DNS A-record query. 不依賴系統 resolver。, _udp_dns_query()

### Community 79 - "Community 79"
Cohesion: 0.36
Nodes (7): analyze_sentiment(), fetch_cnbc_news(), fetch_ptt_stock_board(), fetch_yahoo_finance_news(), get_daily_news_summary(), ETF_TW Pro - 情報爬蟲模組 掃描財經新聞、社群情緒、總經數據, 分析文字情緒 (簡易版，後續會用 AI 優化)     回傳值：-1 (極度利空) 到 1 (極度利多)

### Community 80 - "Community 80"
Cohesion: 0.32
Nodes (8): [DOC] shioaji-useful-links, [H2] 目的, [H2] 官方入口, [H3] 1. snapshots, [H3] 2. ticks, [H3] 3. kbars, [H2] 401 / 權限 / 憑證相關備忘, [H1] Shioaji Useful Links and Notes

### Community 81 - "Community 81"
Cohesion: 0.32
Nodes (8): [DOC] CRON_PACK_STANDARD, [H2] 目的, [H2] 核心原則, [H3] 落地註冊（真新增 cron jobs）, [H3] Dry-run（只列出待新增，不落地）, [H1] ETF_TW Standard Cron Pack, [H2] Pack 內容（目前）, [H3] 透過 setup_agent.py 一鍵初始化（新機器推薦）

### Community 82 - "Community 82"
Cohesion: 0.38
Nodes (5): DummyContract, DummyInnerOrder, DummyStatus, DummyTrade, test_sinopac_normalizer_sets_source_metadata()

### Community 83 - "Community 83"
Cohesion: 0.29
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 0.48
Nodes (6): build_standard_jobs(), cron_add_job(), cron_list_payload(), extract_dedupe_keys(), main(), Land job via CLI flags only (stable).

### Community 85 - "Community 85"
Cohesion: 0.43
Nodes (4): derive_state_dir(), main(), root_sensitive_present(), verdict()

### Community 86 - "Community 86"
Cohesion: 0.38
Nodes (6): is_port_open(), manage(), Check if the dashboard port is responding., Execute the dashboard startup for a specific agent., Main management loop., start_instance()

### Community 87 - "Community 87"
Cohesion: 0.43
Nodes (7): [DOC] STRUCTURE_AUDIT_2026-03-26, [H2] 結論, [H2] 真實結構摘要, [H3] 根目錄主要檔案, [H3] adapter 腳本舉例, [H3] etf_core 仍存在, [H1] ETF_TW 結構盤點與修正說明（2026-03-26）

### Community 88 - "Community 88"
Cohesion: 0.29
Nodes (7): [DOC] SOUL, [H3] 1. 數據優先 (State-First Analysis), [H3] 2. 儀表板察覺 (Dashboard-Awareness), [H3] 3. 策略鐵律 (Taiwan ETF Strategy), [H2] 核心行為準則 (Core Operating Protocols), [H1] ETF_TW Pro Intelligence Agent SOUL, [H2] 回報格式規範 (Reporting Style)

### Community 89 - "Community 89"
Cohesion: 0.47
Nodes (3): DummyOrder, test_order_landed_requires_order_id_and_landed_status(), test_order_terminal_only_for_terminal_statuses()

### Community 90 - "Community 90"
Cohesion: 0.47
Nodes (5): DummyContract, DummyInnerOrder, DummyStatus, DummyTrade, test_normalize_sinopac_callback_maps_trade_objects_into_order_row()

### Community 91 - "Community 91"
Cohesion: 0.47
Nodes (5): DummyContract, DummyInnerOrder, DummyStatus, DummyTrade, test_callback_bridge_sends_normalized_payload_to_state_handler()

### Community 92 - "Community 92"
Cohesion: 0.6
Nodes (5): fetch_tpex(), fetch_twse(), _http_json(), main(), Fetch JSON with a robust strategy.      Rationale:     - Some macOS Python build

### Community 93 - "Community 93"
Cohesion: 0.6
Nodes (5): build_summary(), freshness_text(), load_state(), main(), parse_ts()

### Community 94 - "Community 94"
Cohesion: 0.7
Nodes (4): make_order(), test_verification_payload_marks_unverified_when_broker_missing(), test_verification_payload_marks_unverified_when_ids_do_not_match(), test_verification_payload_marks_verified_when_ids_match()

### Community 95 - "Community 95"
Cohesion: 0.7
Nodes (4): load(), test_open_orders_symbols_do_not_appear_in_positions_until_filled(), test_open_orders_symbols_do_not_force_holdings_into_snapshot_until_filled(), test_positions_and_snapshot_symbols_remain_aligned_for_live_holdings()

### Community 96 - "Community 96"
Cohesion: 0.4
Nodes (0): 

### Community 97 - "Community 97"
Cohesion: 0.4
Nodes (0): 

### Community 98 - "Community 98"
Cohesion: 0.4
Nodes (0): 

### Community 99 - "Community 99"
Cohesion: 0.4
Nodes (0): 

### Community 100 - "Community 100"
Cohesion: 0.7
Nodes (4): atomic_save_json(), classify_symbol_signal(), main(), safe_load_json()

### Community 101 - "Community 101"
Cohesion: 0.7
Nodes (4): compare_etfs(), _highlight_distribution(), _highlight_fee(), _highlight_suitability()

### Community 102 - "Community 102"
Cohesion: 0.6
Nodes (4): main(), _maybe_set_agent_from_state_dir(), If first arg looks like a state_dir, set OPENCLAW_AGENT_NAME and drop it from ar, _run_script()

### Community 103 - "Community 103"
Cohesion: 0.4
Nodes (0): 

### Community 104 - "Community 104"
Cohesion: 0.4
Nodes (1): ETF_Master - Telegram 推送模組 直接調用 OpenClaw 的 message 工具進行推送

### Community 105 - "Community 105"
Cohesion: 0.4
Nodes (5): [DOC] RELEASE_NOTES_v1.0.0, [H1] ETF_TW Release Notes v1.0.0, [H2] Highlights, [H2] Notes, [H2] Packaging policy

### Community 106 - "Community 106"
Cohesion: 0.4
Nodes (5): [DOC] BOOT, [H2] 核心能力連結, [H2] 技能對齊協定 (Agent Alignment Protocol), [H1] ETF Dashboard Boot & Alignment Sequence, [H2] 啟動服務 (Start Services)

### Community 107 - "Community 107"
Cohesion: 0.5
Nodes (5): [DOC] LAYERED_REVIEW_SCHEDULING, [H2] 目的, [H2] 原則, [H1] Layered Review Scheduling, [H2] 目前 Runner

### Community 108 - "Community 108"
Cohesion: 0.4
Nodes (5): [DOC] AGENTS, [H2] 開機引導, [H2] 🚨 交易時段硬約束（所有衍生智能體必須遵守）, [H1] AGENTS.md, [H2] 🛠️ 儀表板維護 (Dashboard Maintenance)

### Community 109 - "Community 109"
Cohesion: 0.5
Nodes (0): 

### Community 110 - "Community 110"
Cohesion: 0.83
Nodes (3): make_order(), test_complete_trade_style_verification_blocks_unmatched_submit(), test_complete_trade_style_verification_requires_broker_match()

### Community 111 - "Community 111"
Cohesion: 0.5
Nodes (0): 

### Community 112 - "Community 112"
Cohesion: 0.5
Nodes (0): 

### Community 113 - "Community 113"
Cohesion: 0.5
Nodes (0): 

### Community 114 - "Community 114"
Cohesion: 0.5
Nodes (0): 

### Community 115 - "Community 115"
Cohesion: 0.5
Nodes (0): 

### Community 116 - "Community 116"
Cohesion: 0.5
Nodes (0): 

### Community 117 - "Community 117"
Cohesion: 0.5
Nodes (0): 

### Community 118 - "Community 118"
Cohesion: 0.83
Nodes (3): classify_level(), event_hash(), main()

### Community 119 - "Community 119"
Cohesion: 0.83
Nodes (3): _build_agent_reasoning(), generate_ai_agent_response_from_state_dir(), _load_json()

### Community 120 - "Community 120"
Cohesion: 0.83
Nodes (3): build_layered_review_status(), _load_json(), main()

### Community 121 - "Community 121"
Cohesion: 0.83
Nodes (3): generate_response_payload_from_state_dir(), _load_json(), _pick_candidate()

### Community 122 - "Community 122"
Cohesion: 0.5
Nodes (4): [DOC] source_health_matrix, [H2] 更新紀錄, [H2] 如何更新？, [H1] Source Health & Fetchability Matrix

### Community 123 - "Community 123"
Cohesion: 0.67
Nodes (4): [DOC] risk-signal, [H2] 核心訊號表, [H2] 活躍風險事件, [H1] 風險訊號總覽 (Risk Signal)

### Community 124 - "Community 124"
Cohesion: 0.67
Nodes (0): 

### Community 125 - "Community 125"
Cohesion: 0.67
Nodes (0): 

### Community 126 - "Community 126"
Cohesion: 0.67
Nodes (0): 

### Community 127 - "Community 127"
Cohesion: 0.67
Nodes (0): 

### Community 128 - "Community 128"
Cohesion: 0.67
Nodes (0): 

### Community 129 - "Community 129"
Cohesion: 0.67
Nodes (0): 

### Community 130 - "Community 130"
Cohesion: 0.67
Nodes (0): 

### Community 131 - "Community 131"
Cohesion: 0.67
Nodes (0): 

### Community 132 - "Community 132"
Cohesion: 0.67
Nodes (0): 

### Community 133 - "Community 133"
Cohesion: 0.67
Nodes (0): 

### Community 134 - "Community 134"
Cohesion: 0.67
Nodes (0): 

### Community 135 - "Community 135"
Cohesion: 0.67
Nodes (0): 

### Community 136 - "Community 136"
Cohesion: 0.67
Nodes (0): 

### Community 137 - "Community 137"
Cohesion: 0.67
Nodes (0): 

### Community 138 - "Community 138"
Cohesion: 0.67
Nodes (0): 

### Community 139 - "Community 139"
Cohesion: 0.67
Nodes (0): 

### Community 140 - "Community 140"
Cohesion: 0.67
Nodes (0): 

### Community 141 - "Community 141"
Cohesion: 0.67
Nodes (0): 

### Community 142 - "Community 142"
Cohesion: 0.67
Nodes (0): 

### Community 143 - "Community 143"
Cohesion: 0.67
Nodes (0): 

### Community 144 - "Community 144"
Cohesion: 0.67
Nodes (0): 

### Community 145 - "Community 145"
Cohesion: 0.67
Nodes (0): 

### Community 146 - "Community 146"
Cohesion: 0.67
Nodes (0): 

### Community 147 - "Community 147"
Cohesion: 0.67
Nodes (0): 

### Community 148 - "Community 148"
Cohesion: 0.67
Nodes (0): 

### Community 149 - "Community 149"
Cohesion: 0.67
Nodes (0): 

### Community 150 - "Community 150"
Cohesion: 0.67
Nodes (0): 

### Community 151 - "Community 151"
Cohesion: 0.67
Nodes (0): 

### Community 152 - "Community 152"
Cohesion: 0.67
Nodes (0): 

### Community 153 - "Community 153"
Cohesion: 0.67
Nodes (0): 

### Community 154 - "Community 154"
Cohesion: 0.67
Nodes (0): 

### Community 155 - "Community 155"
Cohesion: 0.67
Nodes (0): 

### Community 156 - "Community 156"
Cohesion: 0.67
Nodes (0): 

### Community 157 - "Community 157"
Cohesion: 0.67
Nodes (0): 

### Community 158 - "Community 158"
Cohesion: 0.67
Nodes (0): 

### Community 159 - "Community 159"
Cohesion: 0.67
Nodes (0): 

### Community 160 - "Community 160"
Cohesion: 0.67
Nodes (0): 

### Community 161 - "Community 161"
Cohesion: 0.67
Nodes (0): 

### Community 162 - "Community 162"
Cohesion: 0.67
Nodes (0): 

### Community 163 - "Community 163"
Cohesion: 0.67
Nodes (0): 

### Community 164 - "Community 164"
Cohesion: 0.67
Nodes (0): 

### Community 165 - "Community 165"
Cohesion: 0.67
Nodes (0): 

### Community 166 - "Community 166"
Cohesion: 0.67
Nodes (0): 

### Community 167 - "Community 167"
Cohesion: 0.67
Nodes (0): 

### Community 168 - "Community 168"
Cohesion: 0.67
Nodes (0): 

### Community 169 - "Community 169"
Cohesion: 0.67
Nodes (0): 

### Community 170 - "Community 170"
Cohesion: 0.67
Nodes (0): 

### Community 171 - "Community 171"
Cohesion: 0.67
Nodes (0): 

### Community 172 - "Community 172"
Cohesion: 0.67
Nodes (0): 

### Community 173 - "Community 173"
Cohesion: 0.67
Nodes (0): 

### Community 174 - "Community 174"
Cohesion: 0.67
Nodes (0): 

### Community 175 - "Community 175"
Cohesion: 0.67
Nodes (0): 

### Community 176 - "Community 176"
Cohesion: 0.67
Nodes (0): 

### Community 177 - "Community 177"
Cohesion: 0.67
Nodes (0): 

### Community 178 - "Community 178"
Cohesion: 0.67
Nodes (0): 

### Community 179 - "Community 179"
Cohesion: 0.67
Nodes (0): 

### Community 180 - "Community 180"
Cohesion: 0.67
Nodes (0): 

### Community 181 - "Community 181"
Cohesion: 0.67
Nodes (0): 

### Community 182 - "Community 182"
Cohesion: 0.67
Nodes (0): 

### Community 183 - "Community 183"
Cohesion: 0.67
Nodes (0): 

### Community 184 - "Community 184"
Cohesion: 1.0
Nodes (2): build_strategy_payload(), main()

### Community 185 - "Community 185"
Cohesion: 0.67
Nodes (2): get_best_source(), Returns the recommended source domain based on task and mode.

### Community 186 - "Community 186"
Cohesion: 1.0
Nodes (2): load_jsonl(), main()

### Community 187 - "Community 187"
Cohesion: 1.0
Nodes (2): clamp(), main()

### Community 188 - "Community 188"
Cohesion: 1.0
Nodes (0): 

### Community 189 - "Community 189"
Cohesion: 1.0
Nodes (0): 

### Community 190 - "Community 190"
Cohesion: 1.0
Nodes (0): 

### Community 191 - "Community 191"
Cohesion: 1.0
Nodes (0): 

### Community 192 - "Community 192"
Cohesion: 1.0
Nodes (0): 

### Community 193 - "Community 193"
Cohesion: 1.0
Nodes (0): 

### Community 194 - "Community 194"
Cohesion: 1.0
Nodes (0): 

### Community 195 - "Community 195"
Cohesion: 1.0
Nodes (0): 

### Community 196 - "Community 196"
Cohesion: 1.0
Nodes (0): 

### Community 197 - "Community 197"
Cohesion: 1.0
Nodes (0): 

### Community 198 - "Community 198"
Cohesion: 1.0
Nodes (0): 

### Community 199 - "Community 199"
Cohesion: 1.0
Nodes (0): 

### Community 200 - "Community 200"
Cohesion: 1.0
Nodes (0): 

### Community 201 - "Community 201"
Cohesion: 1.0
Nodes (0): 

### Community 202 - "Community 202"
Cohesion: 1.0
Nodes (0): 

### Community 203 - "Community 203"
Cohesion: 1.0
Nodes (0): 

### Community 204 - "Community 204"
Cohesion: 1.0
Nodes (0): 

### Community 205 - "Community 205"
Cohesion: 1.0
Nodes (0): 

### Community 206 - "Community 206"
Cohesion: 1.0
Nodes (0): 

### Community 207 - "Community 207"
Cohesion: 1.0
Nodes (0): 

### Community 208 - "Community 208"
Cohesion: 1.0
Nodes (0): 

### Community 209 - "Community 209"
Cohesion: 1.0
Nodes (0): 

### Community 210 - "Community 210"
Cohesion: 1.0
Nodes (0): 

### Community 211 - "Community 211"
Cohesion: 1.0
Nodes (0): 

### Community 212 - "Community 212"
Cohesion: 1.0
Nodes (0): 

### Community 213 - "Community 213"
Cohesion: 1.0
Nodes (0): 

### Community 214 - "Community 214"
Cohesion: 1.0
Nodes (0): 

### Community 215 - "Community 215"
Cohesion: 1.0
Nodes (0): 

### Community 216 - "Community 216"
Cohesion: 1.0
Nodes (0): 

### Community 217 - "Community 217"
Cohesion: 1.0
Nodes (0): 

### Community 218 - "Community 218"
Cohesion: 1.0
Nodes (0): 

### Community 219 - "Community 219"
Cohesion: 1.0
Nodes (0): 

### Community 220 - "Community 220"
Cohesion: 1.0
Nodes (0): 

### Community 221 - "Community 221"
Cohesion: 1.0
Nodes (0): 

### Community 222 - "Community 222"
Cohesion: 1.0
Nodes (0): 

### Community 223 - "Community 223"
Cohesion: 1.0
Nodes (0): 

### Community 224 - "Community 224"
Cohesion: 1.0
Nodes (0): 

### Community 225 - "Community 225"
Cohesion: 1.0
Nodes (0): 

### Community 226 - "Community 226"
Cohesion: 1.0
Nodes (0): 

### Community 227 - "Community 227"
Cohesion: 1.0
Nodes (0): 

### Community 228 - "Community 228"
Cohesion: 1.0
Nodes (0): 

### Community 229 - "Community 229"
Cohesion: 1.0
Nodes (0): 

### Community 230 - "Community 230"
Cohesion: 1.0
Nodes (0): 

### Community 231 - "Community 231"
Cohesion: 1.0
Nodes (0): 

### Community 232 - "Community 232"
Cohesion: 1.0
Nodes (0): 

### Community 233 - "Community 233"
Cohesion: 1.0
Nodes (0): 

### Community 234 - "Community 234"
Cohesion: 1.0
Nodes (0): 

### Community 235 - "Community 235"
Cohesion: 1.0
Nodes (0): 

### Community 236 - "Community 236"
Cohesion: 1.0
Nodes (0): 

### Community 237 - "Community 237"
Cohesion: 1.0
Nodes (0): 

### Community 238 - "Community 238"
Cohesion: 1.0
Nodes (0): 

### Community 239 - "Community 239"
Cohesion: 1.0
Nodes (0): 

### Community 240 - "Community 240"
Cohesion: 1.0
Nodes (0): 

### Community 241 - "Community 241"
Cohesion: 1.0
Nodes (0): 

### Community 242 - "Community 242"
Cohesion: 1.0
Nodes (0): 

### Community 243 - "Community 243"
Cohesion: 1.0
Nodes (0): 

### Community 244 - "Community 244"
Cohesion: 1.0
Nodes (0): 

### Community 245 - "Community 245"
Cohesion: 1.0
Nodes (0): 

### Community 246 - "Community 246"
Cohesion: 1.0
Nodes (0): 

### Community 247 - "Community 247"
Cohesion: 1.0
Nodes (0): 

### Community 248 - "Community 248"
Cohesion: 1.0
Nodes (0): 

### Community 249 - "Community 249"
Cohesion: 1.0
Nodes (0): 

### Community 250 - "Community 250"
Cohesion: 1.0
Nodes (0): 

### Community 251 - "Community 251"
Cohesion: 1.0
Nodes (0): 

### Community 252 - "Community 252"
Cohesion: 1.0
Nodes (0): 

### Community 253 - "Community 253"
Cohesion: 1.0
Nodes (0): 

### Community 254 - "Community 254"
Cohesion: 1.0
Nodes (0): 

### Community 255 - "Community 255"
Cohesion: 1.0
Nodes (0): 

### Community 256 - "Community 256"
Cohesion: 1.0
Nodes (0): 

### Community 257 - "Community 257"
Cohesion: 1.0
Nodes (0): 

### Community 258 - "Community 258"
Cohesion: 1.0
Nodes (0): 

### Community 259 - "Community 259"
Cohesion: 1.0
Nodes (0): 

### Community 260 - "Community 260"
Cohesion: 1.0
Nodes (0): 

### Community 261 - "Community 261"
Cohesion: 1.0
Nodes (0): 

### Community 262 - "Community 262"
Cohesion: 1.0
Nodes (0): 

### Community 263 - "Community 263"
Cohesion: 1.0
Nodes (0): 

### Community 264 - "Community 264"
Cohesion: 1.0
Nodes (0): 

### Community 265 - "Community 265"
Cohesion: 1.0
Nodes (0): 

### Community 266 - "Community 266"
Cohesion: 1.0
Nodes (0): 

### Community 267 - "Community 267"
Cohesion: 1.0
Nodes (0): 

### Community 268 - "Community 268"
Cohesion: 1.0
Nodes (2): [DOC] IDENTITY, [H1] IDENTITY.md

### Community 269 - "Community 269"
Cohesion: 1.0
Nodes (0): 

### Community 270 - "Community 270"
Cohesion: 1.0
Nodes (0): 

### Community 271 - "Community 271"
Cohesion: 1.0
Nodes (0): 

### Community 272 - "Community 272"
Cohesion: 1.0
Nodes (0): 

### Community 273 - "Community 273"
Cohesion: 1.0
Nodes (1): Connect to the broker's API

### Community 274 - "Community 274"
Cohesion: 1.0
Nodes (1): Get cash balance and purchasing power

### Community 275 - "Community 275"
Cohesion: 1.0
Nodes (1): Get current stock/ETF holdings

### Community 276 - "Community 276"
Cohesion: 1.0
Nodes (1): Place an order         action: 'BUY' or 'SELL'         order_type: 'MARKET' or '

### Community 277 - "Community 277"
Cohesion: 1.0
Nodes (1): ETF 00878

### Community 278 - "Community 278"
Cohesion: 1.0
Nodes (1): [CODE] from scripts.adapters.sinopac_adapter_enhanced import Sinopa...

### Community 279 - "Community 279"
Cohesion: 1.0
Nodes (1): [CODE] 參考價：76.2
漲停：83.8
跌停：68.6
有效：True
警告：[]...

### Community 280 - "Community 280"
Cohesion: 1.0
Nodes (1): [CODE] from scripts.adapters.base import Order

# 建立訂單
order = Orde...

### Community 281 - "Community 281"
Cohesion: 1.0
Nodes (1): [CODE] # 定義回調函數
def my_order_callback(api, order, status):
    prin...

### Community 282 - "Community 282"
Cohesion: 1.0
Nodes (1): [CODE] limits = await adapter.query_trade_limits()

if limits['can_...

### Community 283 - "Community 283"
Cohesion: 1.0
Nodes (1): [CODE] import asyncio
from scripts.adapters.sinopac_adapter_enhance...

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (1): [CODE] # 檢查漲停價
result = await adapter.check_price_limits('0050', 85...

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (1): [CODE] orders = [
    Order(symbol='0050', action='buy', quantity=1...

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (1): [CODE] # 建立虛擬環境
python -m venv .venv

# 激活虛擬環境 (Windows)
.venv\Scri...

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (1): [CODE] cd ETF_TW
ls -la
# 應包含：SKILL.md, scripts/, references/, data...

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (1): [CODE] # 此指令會自動檢查環境、安裝缺失套件、建立配置與帳本
python scripts/etf_tw.py init --...

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (1): [CODE] pip install yfinance pandas numpy shioaji...

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py check --install-deps...

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py check --install-deps...

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── SKILL.md                    # 技能定義文件（OpenClaw 讀取...

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (1): [CODE] # 統一入口
python scripts/etf_tw.py query 0050
python scripts/et...

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): [CODE] cp assets/config.example.json assets/config.json...

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): [CODE] {
  "trading": {
    "default_mode": "paper",
    "default_b...

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): [CODE] python -m pip install -r scripts/etf_core/requirements.txt...

### Community 297 - "Community 297"
Cohesion: 1.0
Nodes (1): [CODE] yfinance>=0.2.0
pandas>=2.0.0
numpy>=1.24.0...

### Community 298 - "Community 298"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/account_manager.py init --account paper_lab ...

### Community 299 - "Community 299"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/paper_trade.py init-holding --etf 0050 --sha...

### Community 300 - "Community 300"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py --check...

### Community 301 - "Community 301"
Cohesion: 1.0
Nodes (1): [CODE] ✓ Python 環境：OK
✓ 依賴套件：OK
✓ 資料庫連接：OK
✓ ETF 資料：OK
✓ 券商配置：OK...

### Community 302 - "Community 302"
Cohesion: 1.0
Nodes (1): [CODE] cd ~/.openclaw/skills/ETF_TW
git pull origin main
# 或
clawhu...

### Community 303 - "Community 303"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/sync_strategy_link.py
python scripts/sync_pap...

### Community 304 - "Community 304"
Cohesion: 1.0
Nodes (1): [CODE] # 測試 1: 正常小額交易 (100 股)
有效：True
錯誤：[]
警告：[]  # ✅ 無警告，正常

# 測試...

### Community 305 - "Community 305"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py submit-preview --symbol 0050 --side...

### Community 306 - "Community 306"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py submit-preview --symbol 0050 --side...

### Community 307 - "Community 307"
Cohesion: 1.0
Nodes (1): [CODE] cd ~/.openclaw/skills/ETF_TW
git pull...

### Community 308 - "Community 308"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/setup_agent.py --link etf_master...

### Community 309 - "Community 309"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/setup_agent.py --new etf_pro_advisor...

### Community 310 - "Community 310"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/setup_agent.py --list...

### Community 311 - "Community 311"
Cohesion: 1.0
Nodes (1): [CODE] .venv/bin/python scripts/sync_etf_universe_tw.py...

### Community 312 - "Community 312"
Cohesion: 1.0
Nodes (1): ETF 00679B

### Community 313 - "Community 313"
Cohesion: 1.0
Nodes (1): [CODE] api = sj.Shioaji(simulation=True)  # 模擬環境
api = sj.Shioaji(s...

### Community 314 - "Community 314"
Cohesion: 1.0
Nodes (1): [CODE] balance = api.account_balance(stock_acc)...

### Community 315 - "Community 315"
Cohesion: 1.0
Nodes (1): [CODE] positions = api.list_positions(stock_acc)...

### Community 316 - "Community 316"
Cohesion: 1.0
Nodes (1): [CODE] contract = api.Contracts.Stocks.TSE['0050']...

### Community 317 - "Community 317"
Cohesion: 1.0
Nodes (1): [CODE] trades = api.list_trades()...

### Community 318 - "Community 318"
Cohesion: 1.0
Nodes (1): [CODE] from shioaji.constant import Action, OrderType, StockPriceTy...

### Community 319 - "Community 319"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── SKILL.md
├── TASKS.md
├── INSTALL.md
├── README....

### Community 320 - "Community 320"
Cohesion: 1.0
Nodes (1): [CODE] # 計算 Python 腳本數量
find scripts -name "*.py" -not -path "*/__p...

### Community 321 - "Community 321"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── SKILL.md                    # 本文件
├── data/
│   ...

### Community 322 - "Community 322"
Cohesion: 1.0
Nodes (1): [CODE] 2. **環境點檢**：...

### Community 323 - "Community 323"
Cohesion: 1.0
Nodes (1): [CODE] 3. **自動初始化**：...

### Community 324 - "Community 324"
Cohesion: 1.0
Nodes (1): [CODE] 4. **查看資產回報** (老手常用)：...

### Community 325 - "Community 325"
Cohesion: 1.0
Nodes (1): [CODE] *此指令會計算實現/未實現損益與總報酬。*
   *此指令會自動補齊缺失套件、建立 `assets/config.jso...

### Community 326 - "Community 326"
Cohesion: 1.0
Nodes (1): [CODE] ### 2. 重要規範
- **帳戶別名**：應與 `trading_mode.json` 中的 `default_ac...

### Community 327 - "Community 327"
Cohesion: 1.0
Nodes (1): [CODE] 並將輸出的口語範例呈現給用戶，引導用戶開始互動。

---

## 操作指引

### 當使用者需要 ETF 基本資料
...

### Community 328 - "Community 328"
Cohesion: 1.0
Nodes (1): [CODE] ---

## Decision Provenance Logger（決策溯源記錄器）

### 核心概念
每次決策（p...

### Community 329 - "Community 329"
Cohesion: 1.0
Nodes (1): [CODE] **F1 已修復**：POST `/api/auto-trade/submit` 端點（4道Gate確認機制）
- Ga...

### Community 330 - "Community 330"
Cohesion: 1.0
Nodes (1): [CODE] **mode 標記**：
- Tier 1 → `mode: "preview-only"`（正常）
- Tier 2 ...

### Community 331 - "Community 331"
Cohesion: 1.0
Nodes (1): [CODE] **資料來源**（唯讀、不改原始格式）：
- `decision_log.jsonl` — 決策掃描紀錄
- `auto...

### Community 332 - "Community 332"
Cohesion: 1.0
Nodes (1): [CODE] **CLI 使用**：...

### Community 333 - "Community 333"
Cohesion: 1.0
Nodes (1): [CODE] **Dashboard API**：
- `GET /api/trade-journal` — 列出所有可用歸檔日期
-...

### Community 334 - "Community 334"
Cohesion: 1.0
Nodes (1): [CODE] **2. 重大事件偵測**...

### Community 335 - "Community 335"
Cohesion: 1.0
Nodes (1): [CODE] **3. 決策引擎刷新**...

### Community 336 - "Community 336"
Cohesion: 1.0
Nodes (1): [CODE] **4. Wiki 知識更新（判讀層）**

注意：State 檔案名稱對照
- 重大事件觸發檔案：`major_eve...

### Community 337 - "Community 337"
Cohesion: 1.0
Nodes (1): ETF 00929

### Community 338 - "Community 338"
Cohesion: 1.0
Nodes (1): ETF 00892

### Community 339 - "Community 339"
Cohesion: 1.0
Nodes (1): ETF 00923

### Community 340 - "Community 340"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py init --install-deps...

### Community 341 - "Community 341"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py check...

### Community 342 - "Community 342"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py list
  python scripts/etf_tw.py sea...

### Community 343 - "Community 343"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py compare 0050 006208...

### Community 344 - "Community 344"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py calc 0050 10000 10 --annual-return ...

### Community 345 - "Community 345"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py portfolio...

### Community 346 - "Community 346"
Cohesion: 1.0
Nodes (1): [CODE] python scripts/etf_tw.py paper-trade --symbol 0050 --side bu...

### Community 347 - "Community 347"
Cohesion: 1.0
Nodes (1): [CODE] bash scripts/start_dashboard.sh...

### Community 348 - "Community 348"
Cohesion: 1.0
Nodes (1): [CODE] cd ~/.openclaw/skills/ETF_TW && .venv/bin/python3 -m uvicorn...

### Community 349 - "Community 349"
Cohesion: 1.0
Nodes (1): [CODE] validate → preview → confirm → execute...

### Community 350 - "Community 350"
Cohesion: 1.0
Nodes (1): [CODE] 使用者：買進 0050 100 股

Validate 結果：
✅ 標的有效：0050.TW
✅ 數量合理：100 股
...

### Community 351 - "Community 351"
Cohesion: 1.0
Nodes (1): [CODE] 使用者：買進 0050 100 股 @ 75 元

Preview 結果：
┌─────────────────────...

### Community 352 - "Community 352"
Cohesion: 1.0
Nodes (1): [CODE] ✅ 買進成功！
0050 x 100 股 @ 75.00 元

持倉更新：
- 0050: 100 股（平均成本 75....

### Community 353 - "Community 353"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 單位混淆警告！

您輸入：400 張 0050 = 40,000 股
目前帳戶總值：約 25,000 元
單筆交易...

### Community 354 - "Community 354"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 大額交易警告！

單筆交易價值：1,500,000 元
目前總持倉：2,000,000 元
占比：75%（超過 5...

### Community 355 - "Community 355"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 訊號衝突！

技術面：
- RSI: 28（超賣，買進訊號）
- MA20: 股價跌破（賣出訊號）

基本面：
-...

### Community 356 - "Community 356"
Cohesion: 1.0
Nodes (1): [CODE] ## 交易紀錄

| 日期 | 時間 | 標的 | 動作 | 價格 | 股數 | 金額 | 手續費 | 備註 |
|--...

### Community 357 - "Community 357"
Cohesion: 1.0
Nodes (1): [CODE] ## 當前持倉摘要（截至 2026-03-17 23:49）

| 標的 | 總股數 | 平均成本 | 當前價格 | 未...

### Community 358 - "Community 358"
Cohesion: 1.0
Nodes (1): [CODE] ❌ 驗證失敗

原因：現金不足
需要：7,510.69 元
目前：5,000 元

請增加現金或減少交易數量...

### Community 359 - "Community 359"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 資料提示：
- 股價為 2026-03-23 收盤價
- 非即時報價
- 實際成交價可能不同...

### Community 360 - "Community 360"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 免責聲明：
- 技術指標僅供參考
- 不構成投資建議
- 過去表現不代表未來...

### Community 361 - "Community 361"
Cohesion: 1.0
Nodes (1): [CODE] ⚠️ 資料限制：
- 該 ETF 費用率資料缺失
- 無法取得最新配息紀錄
- 建議交叉驗證其他來源...

### Community 362 - "Community 362"
Cohesion: 1.0
Nodes (1): [CODE] ## Data Update Log (YYYY-MM-DD)
- **標的**: [ETF 代號]
- **更新項目*...

### Community 363 - "Community 363"
Cohesion: 1.0
Nodes (1): [CODE] ## Data Update Log (2026-03-23)
- **標的**: 0050, 006208
- **更...

### Community 364 - "Community 364"
Cohesion: 1.0
Nodes (1): [CODE] 關鍵問題：什麼叫「自主判斷」？

目前架構：
ETF_master → 讀取 market cache → 決定買什麼 ...

### Community 365 - "Community 365"
Cohesion: 1.0
Nodes (1): [CODE] 目前的風控：
- 交易時段檢查 ✅
- Pre-flight 檢查 ✅
- 風控規則（集中度、單位混淆）✅

但缺少：
...

### Community 366 - "Community 366"
Cohesion: 1.0
Nodes (1): [CODE] 現有層級（推測）：
├── 記錄預測與實際結果
├── 計算準確率
└── 人類可查看報告

缺少層級：
❌ 自動調整決...

### Community 367 - "Community 367"
Cohesion: 1.0
Nodes (1): [CODE] 目前問題：
- 需要手動讓 ETF_master「跑測、修改斷掉的鏈路」
- state 檔案（如 auto_submi...

### Community 368 - "Community 368"
Cohesion: 1.0
Nodes (1): [CODE] 關鍵問題：什麼是「利潤最大化」？

風險：
❌ 如果目標函數只是「報酬率」，Agent 可能過度冒險
❌ 如果沒有考慮「...

### Community 369 - "Community 369"
Cohesion: 1.0
Nodes (1): [CODE] 目前：記錄 → 人類查看
應該：記錄 → 分析 → 自動調整參數 → 驗證效果 → 沉澱知識

具體行動：
1. 建立 ...

### Community 370 - "Community 370"
Cohesion: 1.0
Nodes (1): [CODE] 目前：單筆風控、交易時段檢查
應該：組合風控、回撤限制、市場異常偵測

具體行動：
1. 建立「每日虧損上限」→ 觸發後...

### Community 371 - "Community 371"
Cohesion: 1.0
Nodes (1): [CODE] 目前：需要人類維護鏈路、修復 state
應該：自動健康檢查、自動修復、自動通知

具體行動：
1. 建立「健康檢查」c...

### Community 372 - "Community 372"
Cohesion: 1.0
Nodes (1): [CODE] from adapters import get_adapter
from trade_logger import ge...

### Community 373 - "Community 373"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── scripts/
│   ├── adapters/
│   │   ├── base.py
│...

### Community 374 - "Community 374"
Cohesion: 1.0
Nodes (1): [CODE] from scripts.trade_logger import get_logger

logger = get_lo...

### Community 375 - "Community 375"
Cohesion: 1.0
Nodes (1): [CODE] from scripts.risk_controller import get_risk_controller

ris...

### Community 376 - "Community 376"
Cohesion: 1.0
Nodes (1): [CODE] summary = risk_ctrl.get_daily_summary()
print(f"今日訂單數：{summa...

### Community 377 - "Community 377"
Cohesion: 1.0
Nodes (1): [CODE] # 查詢交易日誌
python3 scripts/etf_tw.py trade-logs --symbol 0050....

### Community 378 - "Community 378"
Cohesion: 1.0
Nodes (1): [CODE] # 正式送單必須透過 venv_executor
python scripts/venv_executor.py com...

### Community 379 - "Community 379"
Cohesion: 1.0
Nodes (1): [CODE] # P2: 明確記錄 - 此掃描不影響送單狀態
print(f"[STATE] auto_trade_state 已更新...

### Community 380 - "Community 380"
Cohesion: 1.0
Nodes (1): [CODE] # 執行狀態對帳
python scripts/state_reconciliation_enhanced.py...

### Community 381 - "Community 381"
Cohesion: 1.0
Nodes (1): [CODE] ============================================================...

### Community 382 - "Community 382"
Cohesion: 1.0
Nodes (1): [CODE] # complete_trade.py 第 123-129 行
if mode in ('live', 'sandbox...

### Community 383 - "Community 383"
Cohesion: 1.0
Nodes (1): [CODE] cd skills/ETF_TW
python tests/test_venv_executor.py...

### Community 384 - "Community 384"
Cohesion: 1.0
Nodes (1): [CODE] ============================================================...

### Community 385 - "Community 385"
Cohesion: 1.0
Nodes (1): [CODE] instances/
├── etf_master/
│   └── state/
│       ├── orders...

### Community 386 - "Community 386"
Cohesion: 1.0
Nodes (1): [CODE] commit 099f23a
feat(ETF_TW): 修復正式單變預演與訂單消失問題 (P1-P3)

- P1: ...

### Community 387 - "Community 387"
Cohesion: 1.0
Nodes (1): [CODE] commit e1414f6
test(ETF_TW): 加入 P4-P5 驗證測試

- P4: 交易時段硬閘門測試
...

### Community 388 - "Community 388"
Cohesion: 1.0
Nodes (1): [CODE] # 1. 確認在交易時段
python scripts/venv_executor.py trading_hours_g...

### Community 389 - "Community 389"
Cohesion: 1.0
Nodes (1): [CODE] # 執行完整測試
python tests/test_venv_executor.py

# 檢查健康狀態
python...

### Community 390 - "Community 390"
Cohesion: 1.0
Nodes (1): [CODE] 測試 1：券商註冊表 ✅
測試 2：帳戶配置 ✅
測試 3：適配器實例化 ✅
測試 4：模擬交易完整流程 ✅...

### Community 391 - "Community 391"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py brokers...

### Community 392 - "Community 392"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py accounts...

### Community 393 - "Community 393"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py paper-account orders.json -a defau...

### Community 394 - "Community 394"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/test_phase4.py...

### Community 395 - "Community 395"
Cohesion: 1.0
Nodes (1): [CODE] ## Incident Log (YYYY-MM-DD)
- **Event**: [事件描述]
- **Failure...

### Community 396 - "Community 396"
Cohesion: 1.0
Nodes (1): [CODE] ## Incident Log (2026-03-17)
- **Event**: 使用者請求「400 張 0050」（...

### Community 397 - "Community 397"
Cohesion: 1.0
Nodes (1): [CODE] skills/ETF_TW/.venv/bin/python   # 必須用 project venv...

### Community 398 - "Community 398"
Cohesion: 1.0
Nodes (1): [CODE] contract = api.Contracts.Stocks.TSE.TSE00878           # TSE...

### Community 399 - "Community 399"
Cohesion: 1.0
Nodes (1): [CODE] order = api.Order(
    price=27.25,
    quantity=100,       ...

### Community 400 - "Community 400"
Cohesion: 1.0
Nodes (1): [CODE] trade = api.place_order(contract, order)...

### Community 401 - "Community 401"
Cohesion: 1.0
Nodes (1): [CODE] api.update_status(api.stock_account)
# 確認：status 非 Failed/In...

### Community 402 - "Community 402"
Cohesion: 1.0
Nodes (1): [CODE] api.update_status(api.stock_account)
trades = api.list_trade...

### Community 403 - "Community 403"
Cohesion: 1.0
Nodes (1): [CODE] quantity=1,                                    # 張（1000股）
or...

### Community 404 - "Community 404"
Cohesion: 1.0
Nodes (1): [CODE] api.update_order(trade=trade, price=new_price)
api.update_or...

### Community 405 - "Community 405"
Cohesion: 1.0
Nodes (1): [CODE] positions = api.list_positions(api.stock_account)
balance = ...

### Community 406 - "Community 406"
Cohesion: 1.0
Nodes (1): [CODE] Account:    9A9L / 0737121
Venv:       skills/ETF_TW/.venv/b...

### Community 407 - "Community 407"
Cohesion: 1.0
Nodes (1): ETF 00713

### Community 408 - "Community 408"
Cohesion: 1.0
Nodes (1): ETF 00881

### Community 409 - "Community 409"
Cohesion: 1.0
Nodes (1): ETF 00637L

### Community 410 - "Community 410"
Cohesion: 1.0
Nodes (1): [CODE] snapshots = api.snapshots([api.Contracts.Stocks["2330"]])...

### Community 411 - "Community 411"
Cohesion: 1.0
Nodes (1): [CODE] ticks = api.ticks(api.Contracts.Stocks["2330"], date="2026-0...

### Community 412 - "Community 412"
Cohesion: 1.0
Nodes (1): [CODE] kbars = api.kbars(api.Contracts.Stocks["2330"], start="2026-...

### Community 413 - "Community 413"
Cohesion: 1.0
Nodes (1): [CODE] api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="Y...

### Community 414 - "Community 414"
Cohesion: 1.0
Nodes (1): [CODE] api = sj.Shioaji(simulation=True)...

### Community 415 - "Community 415"
Cohesion: 1.0
Nodes (1): [CODE] api = sj.Shioaji()
api.login(api_key="YOUR_KEY", secret_key=...

### Community 416 - "Community 416"
Cohesion: 1.0
Nodes (1): [CODE] api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="Y...

### Community 417 - "Community 417"
Cohesion: 1.0
Nodes (1): [CODE] curl -LsSf https://astral.sh/uv/install.sh | sh
uv init my-t...

### Community 418 - "Community 418"
Cohesion: 1.0
Nodes (1): [CODE] 🚀 Phase 4 - 多券商架構測試

測試 1：券商註冊表
已載入 4 個券商：
  - sinopac: 永豐金證...

### Community 419 - "Community 419"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── data/
│   ├── broker_registry.json (NEW)
│   └──...

### Community 420 - "Community 420"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py accounts...

### Community 421 - "Community 421"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py brokers...

### Community 422 - "Community 422"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py preview-account orders.json -a my_...

### Community 423 - "Community 423"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/etf_tw.py paper-account orders.json -a defau...

### Community 424 - "Community 424"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/test_phase4.py...

### Community 425 - "Community 425"
Cohesion: 1.0
Nodes (1): [CODE] # 列出 ETF
python3 scripts/etf_tw.py list

# 搜尋
python3 script...

### Community 426 - "Community 426"
Cohesion: 1.0
Nodes (1): [CODE] # 模擬交易（預設）
python3 scripts/complete_trade.py 0050.TW buy 100...

### Community 427 - "Community 427"
Cohesion: 1.0
Nodes (1): [CODE] # 查詢日志
python3 scripts/etf_tw.py trade-logs --symbol 0050.TW...

### Community 428 - "Community 428"
Cohesion: 1.0
Nodes (1): [CODE] 測試：永豐金證券適配器（Scaffold）
=====================================
...

### Community 429 - "Community 429"
Cohesion: 1.0
Nodes (1): [CODE] async def authenticate(self) -> bool:
    # TODO: 實作真實的永豐金 A...

### Community 430 - "Community 430"
Cohesion: 1.0
Nodes (1): [CODE] async def get_market_data(self, symbol: str) -> Dict:
    # ...

### Community 431 - "Community 431"
Cohesion: 1.0
Nodes (1): [CODE] async def submit_order(self, order: Order) -> Order:
    # T...

### Community 432 - "Community 432"
Cohesion: 1.0
Nodes (1): [CODE] # 範例：使用 aiohttp 進行非同步 API 調用
async def _call_api(self, endpo...

### Community 433 - "Community 433"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/
├── scripts/
│   ├── adapters/
│   │   ├── base.py (...

### Community 434 - "Community 434"
Cohesion: 1.0
Nodes (1): [CODE] from adapters.sinopac_adapter import create_sinopac_adapter
...

### Community 435 - "Community 435"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/test_sinopac.py...

### Community 436 - "Community 436"
Cohesion: 1.0
Nodes (1): [CODE] # 使用永豐金帳戶進行模擬交易
python3 scripts/etf_tw.py paper-account orde...

### Community 437 - "Community 437"
Cohesion: 1.0
Nodes (1): [CODE] {
  "kind": "every",
  "everyMs": 86400000
}...

### Community 438 - "Community 438"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/run_etf_tw_task.py auto_post_review_cycle <s...

### Community 439 - "Community 439"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/setup_agent.py --link <instance_id> --init-c...

### Community 440 - "Community 440"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/register_standard_cron_pack.py <instance_id>...

### Community 441 - "Community 441"
Cohesion: 1.0
Nodes (1): [CODE] python3 scripts/register_standard_cron_pack.py <instance_id>...

### Community 442 - "Community 442"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/instances/<agent_id>/state/...

### Community 443 - "Community 443"
Cohesion: 1.0
Nodes (1): [CODE] /Users/tuchengshin/.openclaw/skills/ETF_TW/instances/etf_mas...

### Community 444 - "Community 444"
Cohesion: 1.0
Nodes (1): [CODE] ETF_TW/state/...

### Community 445 - "Community 445"
Cohesion: 1.0
Nodes (1): [CODE] (1) sync_strategy_link.py
(2) sync_live_state.py / sync_pape...

### Community 446 - "Community 446"
Cohesion: 1.0
Nodes (1): [CODE] 【策略：{base_strategy}｜覆蓋：{scenario_overlay}】...

### Community 447 - "Community 447"
Cohesion: 1.0
Nodes (1): ETF 00922

### Community 448 - "Community 448"
Cohesion: 1.0
Nodes (1): [CODE] import shioaji as sj
api = sj.Shioaji()
api.login(
    api_k...

### Community 449 - "Community 449"
Cohesion: 1.0
Nodes (1): [CODE] api = sj.Shioaji()
api.login(
    person_id="YOUR_PERSON_ID"...

### Community 450 - "Community 450"
Cohesion: 1.0
Nodes (1): [CODE] api.login(
    api_key="KEY", secret_key="SECRET",
    contr...

### Community 451 - "Community 451"
Cohesion: 1.0
Nodes (1): [CODE] accounts = api.list_accounts()
# [StockAccount(...), FutureA...

### Community 452 - "Community 452"
Cohesion: 1.0
Nodes (1): [CODE] api.subscribe_trade(account)
api.unsubscribe_trade(account)...

### Community 453 - "Community 453"
Cohesion: 1.0
Nodes (1): [CODE] api.logout()  # → True (注意：會觸發 segfault exit 139，見已知問題)...

### Community 454 - "Community 454"
Cohesion: 1.0
Nodes (1): [CODE] # 不在登入時自動載入
api.login(api_key="KEY", secret_key="SECRET", fe...

### Community 455 - "Community 455"
Cohesion: 1.0
Nodes (1): [CODE] api.login(api_key="KEY", secret_key="SECRET", contracts_time...

### Community 456 - "Community 456"
Cohesion: 1.0
Nodes (1): [CODE] # 方式一：代碼直接查
api.Contracts.Stocks["2890"]

# 方式二：交易所+代碼
api.C...

### Community 457 - "Community 457"
Cohesion: 1.0
Nodes (1): [CODE] api.Contracts.Futures["TXFA3"]
api.Contracts.Futures.TXF.TXF...

### Community 458 - "Community 458"
Cohesion: 1.0
Nodes (1): [CODE] api.Contracts.Indexs.TSE["001"]
# Index(exchange=TSE, code='...

### Community 459 - "Community 459"
Cohesion: 1.0
Nodes (1): [CODE] contract = api.Contracts.Stocks.TSE.TSE2890

order = api.Ord...

### Community 460 - "Community 460"
Cohesion: 1.0
Nodes (1): [CODE] api.place_order(
    contract: shioaji.contracts.Contract,
 ...

### Community 461 - "Community 461"
Cohesion: 1.0
Nodes (1): [CODE] Trade(
    contract=Stock(...),
    order=Order(
        act...

### Community 462 - "Community 462"
Cohesion: 1.0
Nodes (1): [CODE] # 現股買進
action=sj.constant.Action.Buy
order_lot=sj.constant.S...

### Community 463 - "Community 463"
Cohesion: 1.0
Nodes (1): [CODE] contract = api.Contracts.Stocks.TSE.TSE0050

order = api.Ord...

### Community 464 - "Community 464"
Cohesion: 1.0
Nodes (1): [CODE] api.update_status(api.stock_account)
trades = api.list_trade...

### Community 465 - "Community 465"
Cohesion: 1.0
Nodes (1): [CODE] api.update_status(
    account: Account = None,
    trade: T...

### Community 466 - "Community 466"
Cohesion: 1.0
Nodes (1): [CODE] api.update_order(trade=trade, price=17.5)
api.update_status(...

### Community 467 - "Community 467"
Cohesion: 1.0
Nodes (1): [CODE] api.update_order(trade=trade, qty=1)
api.update_status(api.s...

### Community 468 - "Community 468"
Cohesion: 1.0
Nodes (1): [CODE] api.update_order(
    trade: Trade,
    price: Union[int, fl...

### Community 469 - "Community 469"
Cohesion: 1.0
Nodes (1): [CODE] api.cancel_order(trade)
api.update_status(api.stock_account)...

### Community 470 - "Community 470"
Cohesion: 1.0
Nodes (1): [CODE] Deal(seq='000001', price=17, quantity=3, ts=1673501631.62918...

### Community 471 - "Community 471"
Cohesion: 1.0
Nodes (1): [CODE] api.list_positions(api.stock_account)

# 回傳:
# [
#   Positio...

### Community 472 - "Community 472"
Cohesion: 1.0
Nodes (1): [CODE] api.list_positions(
    account: Account = None,
    unit: U...

### Community 473 - "Community 473"
Cohesion: 1.0
Nodes (1): [CODE] api.account_balance()
api.account_balance(account=api.stock_...

### Community 474 - "Community 474"
Cohesion: 1.0
Nodes (1): [CODE] api.account_balance(
    account: Account = None,
    timeou...

### Community 475 - "Community 475"
Cohesion: 1.0
Nodes (1): [CODE] profitloss = api.list_profit_loss(
    api.stock_account,
  ...

### Community 476 - "Community 476"
Cohesion: 1.0
Nodes (1): [CODE] api.list_profit_loss(
    account: Account = None,
    begin...

### Community 477 - "Community 477"
Cohesion: 1.0
Nodes (1): [CODE] detail = api.list_profit_loss_detail(
    api.stock_account,...

### Community 478 - "Community 478"
Cohesion: 1.0
Nodes (1): [CODE] summary = api.list_profit_loss_summary(
    api.stock_accoun...

### Community 479 - "Community 479"
Cohesion: 1.0
Nodes (1): [CODE] api.margin(api.futopt_account)
# Margin(yesterday_balance=60...

### Community 480 - "Community 480"
Cohesion: 1.0
Nodes (1): [CODE] settlements = api.settlements(api.stock_account)

# [
#   Se...

### Community 481 - "Community 481"
Cohesion: 1.0
Nodes (1): [CODE] api.settlements(
    account: Account = None,
    timeout: i...

### Community 482 - "Community 482"
Cohesion: 1.0
Nodes (1): [CODE] api.trading_limits(api.stock_account)

# TradingLimits(
#   ...

### Community 483 - "Community 483"
Cohesion: 1.0
Nodes (1): [CODE] @api.quote.on_event
def event_callback(resp_code: int, event...

### Community 484 - "Community 484"
Cohesion: 1.0
Nodes (1): [CODE] def order_cb(stat, msg):
    print('my_order_callback')
    ...

### Community 485 - "Community 485"
Cohesion: 1.0
Nodes (1): [CODE] {
    'operation': {
        'op_type': 'New',          # Ne...

### Community 486 - "Community 486"
Cohesion: 1.0
Nodes (1): [CODE] {
    'trade_id': '9c6ae2eb',
    'seqno': '269866',
    'or...

### Community 487 - "Community 487"
Cohesion: 1.0
Nodes (1): [CODE] # 漲停價
limit_up = api.calc_limit_up_price(
    price=contract...

### Community 488 - "Community 488"
Cohesion: 1.0
Nodes (1): [CODE] contracts = [api.Contracts.Stocks['2330'], api.Contracts.Sto...

### Community 489 - "Community 489"
Cohesion: 1.0
Nodes (1): [CODE] api.snapshots(
    contracts: List[Contract],
    timeout: i...

### Community 490 - "Community 490"
Cohesion: 1.0
Nodes (1): [CODE] import pandas as pd
df = pd.DataFrame(s.__dict__ for s in sn...

### Community 491 - "Community 491"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...

### Community 492 - "Community 492"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...

### Community 493 - "Community 493"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...

### Community 494 - "Community 494"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.subscribe(
    contract: Contract,
    quote_type:...

### Community 495 - "Community 495"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...

### Community 496 - "Community 496"
Cohesion: 1.0
Nodes (1): [CODE] api.quote.unsubscribe(contract, sj.constant.QuoteType.Tick, ...

### Community 497 - "Community 497"
Cohesion: 1.0
Nodes (1): [CODE] from shioaji import TickSTKv1, Exchange

def quote_callback(...

### Community 498 - "Community 498"
Cohesion: 1.0
Nodes (1): [CODE] from shioaji import BidAskSTKv1, Exchange

def bidask_callba...

### Community 499 - "Community 499"
Cohesion: 1.0
Nodes (1): [CODE] # 事件回呼（訂閱成功/失敗）
api.quote.set_event_callback(func)

# Tick v...

### Community 500 - "Community 500"
Cohesion: 1.0
Nodes (1): [CODE] ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"]...

### Community 501 - "Community 501"
Cohesion: 1.0
Nodes (1): [CODE] api.ticks(
    contract: BaseContract,
    date: str = '2022...

### Community 502 - "Community 502"
Cohesion: 1.0
Nodes (1): [CODE] ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"]...

### Community 503 - "Community 503"
Cohesion: 1.0
Nodes (1): [CODE] kbars = api.kbars(
    contract=api.Contracts.Stocks["2330"]...

### Community 504 - "Community 504"
Cohesion: 1.0
Nodes (1): [CODE] api.kbars(
    contract: BaseContract,
    start: str = '202...

### Community 505 - "Community 505"
Cohesion: 1.0
Nodes (1): [CODE] import pandas as pd

df = pd.DataFrame({**kbars})
df.ts = pd...

### Community 506 - "Community 506"
Cohesion: 1.0
Nodes (1): [CODE] trade = api.place_order(contract, order, timeout=0)
# status...

### Community 507 - "Community 507"
Cohesion: 1.0
Nodes (1): [CODE] api.update_status(api.stock_account, timeout=0)...

### Community 508 - "Community 508"
Cohesion: 1.0
Nodes (1): [CODE] api.cancel_order(trade, timeout=0)...

### Community 509 - "Community 509"
Cohesion: 1.0
Nodes (1): [CODE] import shioaji as sj

api = sj.Shioaji(simulation=True)
acco...

### Community 510 - "Community 510"
Cohesion: 1.0
Nodes (1): [CODE] import shioaji as sj

# 1. 初始化
api = sj.Shioaji()

# 2. 登入
a...

### Community 511 - "Community 511"
Cohesion: 1.0
Nodes (1): [CODE] # 1. 取得合約（注意 OTC 用 .get()）
contract = api.Contracts.Stocks.O...

### Community 512 - "Community 512"
Cohesion: 1.0
Nodes (1): [CODE] import shioaji as sj

# Action
sj.constant.Action.Buy
sj.con...

### Community 513 - "Community 513"
Cohesion: 1.0
Nodes (1): [CODE] {
  "request_id": "string",
  "generated_at": "ISO timestamp...

### Community 514 - "Community 514"
Cohesion: 1.0
Nodes (1): [CODE] {
  "request_id": "string",
  "created_at": "ISO timestamp",...

### Community 515 - "Community 515"
Cohesion: 1.0
Nodes (1): [CODE] {
  "request_id": "string",
  "generated_at": "ISO timestamp...

### Community 516 - "Community 516"
Cohesion: 1.0
Nodes (1): [CODE] python simulator.py...

### Community 517 - "Community 517"
Cohesion: 1.0
Nodes (1): [CODE] python main_service.py...

### Community 518 - "Community 518"
Cohesion: 1.0
Nodes (1): [CODE] from main_service import ETF_TW_Pro

service = ETF_TW_Pro()
...

### Community 519 - "Community 519"
Cohesion: 1.0
Nodes (1): [CODE] result = service.execute_buy('0050.TW', 100)
print(result)...

### Community 520 - "Community 520"
Cohesion: 1.0
Nodes (1): [CODE] report = service.get_portfolio_report()
print(report)...

### Community 521 - "Community 521"
Cohesion: 1.0
Nodes (1): [CODE] 名稱：YUANTA SECURITIES INV TRUST CO
目前價：75.75
昨收：78.75
漲跌：-3.0...

### Community 522 - "Community 522"
Cohesion: 1.0
Nodes (1): [CODE] 1. [Yahoo 財經] 傳承 281 年土地公福氣 竹山紫南宮呷平安丁酒萬人空巷...
   時間：Wed, 04 ...

### Community 523 - "Community 523"
Cohesion: 1.0
Nodes (1): [CODE] 初始現金：1,000,000
總資產：1,000,000...

### Community 524 - "Community 524"
Cohesion: 1.0
Nodes (1): [CODE] 結果：✅ 買進成功！
成交金額：7,510.69 (含手續費)
買進後現金：992,489
持倉總值：7,580...

### Community 525 - "Community 525"
Cohesion: 1.0
Nodes (1): [CODE] 0050.TW: 100 股
  均價：75.00
  現價：75.80
  損益：+80.00 (+1.07%)...

### Community 526 - "Community 526"
Cohesion: 1.0
Nodes (1): [CODE] 市場狀態：盤中
0050.TW: 75.75 (0.00%) - 信號：跌破 MA20
006208.TW: 175.6...

### Community 527 - "Community 527"
Cohesion: 1.0
Nodes (1): [CODE] 現金：992,489
總資產：1,000,069
損益：+69 (+0.01%)

持倉明細:
  0050.TW: 1...

## Knowledge Gaps
- **549 isolated node(s):** `DummyContract`, `DummyInnerOrder`, `DummyContract`, `DummyInnerOrder`, `DummyContract` (+544 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 188`** (2 nodes): `test_partial_fill_summary_boundary.py`, `test_partial_fill_should_not_be_treated_as_complete_holding_in_summary_logic()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 189`** (2 nodes): `test_layered_review_cron_registry_live.py`, `test_extract_dedupe_keys_from_cron_list_payload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 190`** (2 nodes): `test_auto_quality_refresh.py`, `test_auto_refresh_quality_state_writes_ai_decision_quality_json()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 191`** (2 nodes): `test_dashboard_base_template.py`, `test_base_template_contains_fintech_visual_tokens()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 192`** (2 nodes): `test_sync_portfolio_snapshot.py`, `test_build_snapshot_from_memory_extracts_holdings_and_cash()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 193`** (2 nodes): `test_dashboard_filled_reconciliation_overview.py`, `test_overview_api_exposes_filled_reconciliation_block()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 194`** (2 nodes): `test_dashboard_trading_mode_api.py`, `test_trading_mode_request_model_accepts_live()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 195`** (2 nodes): `test_dashboard_state_reconciliation_api.py`, `test_overview_api_exposes_state_reconciliation_block()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 196`** (2 nodes): `test_layered_review_cron_draft.py`, `test_build_cron_jobs_from_plan_returns_three_jobs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 197`** (2 nodes): `test_dashboard_ai_decision_bridge_panel.py`, `test_overview_template_contains_ai_decision_bridge_panel_bindings()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 198`** (2 nodes): `test_refresh_filled_reconciliation_report.py`, `test_refresh_reconciliation_report_creates_state_file()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 199`** (2 nodes): `test_generate_ai_decision_request.py`, `test_generate_request_payload_from_state_dir_writes_request_file()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 200`** (2 nodes): `test_ai_research_method_quality_fields.py`, `test_quality_payload_contains_autoresearch_inspired_fields()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 201`** (2 nodes): `test_dashboard_button_tooltips.py`, `test_overview_template_contains_tooltips_for_review_and_outcome_buttons()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 202`** (2 nodes): `test_market_calendar_tw_fallback.py`, `test_fallback_to_weekday_time_when_calendar_missing_date()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 203`** (2 nodes): `test_generate_aligns_quality_state.py`, `test_dashboard_generate_route_mentions_auto_quality_refresh()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 204`** (2 nodes): `test_dashboard_global_banner_empty_intelligence.py`, `test_overview_template_mentions_empty_intelligence_banner_text()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 205`** (2 nodes): `test_dashboard_ai_source_labels.py`, `test_overview_template_contains_source_and_freshness_labels()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 206`** (2 nodes): `test_dashboard_symbol_normalization.py`, `test_dashboard_normalize_symbol_strips_provider_suffixes()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 207`** (2 nodes): `test_write_layered_review_plan.py`, `test_write_layered_review_plan_writes_state_and_ledger()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 208`** (2 nodes): `test_dashboard_reconciliation_warnings.py`, `test_overview_api_exposes_reconciliation_warnings_block()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 209`** (2 nodes): `test_layered_review_scheduler_hook.py`, `test_scheduler_hook_script_exists()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 210`** (2 nodes): `test_dashboard_overview_api.py`, `test_overview_api_returns_expected_keys()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 211`** (2 nodes): `test_state_files.py`, `test_state_files_exist_and_contain_valid_json()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 212`** (2 nodes): `test_dashboard_ai_control_grouping.py`, `test_overview_template_groups_rule_engine_and_ai_bridge_controls()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 213`** (2 nodes): `test_dashboard_decision_memory_context.py`, `test_overview_template_shows_decision_memory_context_summary()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 214`** (2 nodes): `test_dashboard_snapshot_priority.py`, `test_overview_api_uses_snapshot_backed_account_shape()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 215`** (2 nodes): `test_dashboard_ai_visual_sections.py`, `test_overview_template_has_distinct_rule_engine_and_ai_bridge_sections()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 216`** (2 nodes): `test_readme_mentions_agent_summary.py`, `test_readme_mentions_agent_summary_bridge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 217`** (2 nodes): `test_layered_review_cron_registry.py`, `test_compute_jobs_to_add_filters_existing_dedupe_keys()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 218`** (2 nodes): `test_dashboard_health.py`, `test_dashboard_healthcheck()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 219`** (2 nodes): `test_dashboard_health_api_contract.py`, `test_health_api_exposes_summary_and_reconciliation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 220`** (2 nodes): `test_auto_post_review_market_eval.py`, `test_auto_post_review_cycle_uses_market_cache_to_write_price_delta_note()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 221`** (2 nodes): `test_dashboard_auto_reflection_integration.py`, `test_dashboard_app_wires_auto_reflection_after_review_and_outcome()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 222`** (2 nodes): `test_verify_alignment_reconciliation.py`, `test_reconciliation_summary_shape_for_alignment_diagnostic()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 223`** (2 nodes): `test_filled_reconciliation_state_io.py`, `test_save_and_load_reconciliation_report_roundtrip()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 224`** (2 nodes): `test_dashboard_readme_exists.py`, `test_dashboard_readme_includes_agent_summary_sync()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 225`** (2 nodes): `test_layered_review_cron_job_payloads.py`, `test_build_cron_job_payloads_creates_agent_turn_jobs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 226`** (2 nodes): `test_dashboard_intelligence_health.py`, `test_overview_health_exposes_intelligence_readiness()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 227`** (2 nodes): `test_dashboard_global_banner_filled_reconciliation.py`, `test_overview_template_mentions_global_filled_reconciliation_banner()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 228`** (2 nodes): `test_sinopac_default_callback_registration.py`, `test_register_default_state_callback_is_idempotent()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 229`** (2 nodes): `test_auto_post_review_schedule_contract.py`, `test_auto_post_review_cycle_script_exists_for_future_scheduler_hookup()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 230`** (2 nodes): `test_orders_open_callback_fills_ledger.py`, `test_partial_fill_event_updates_fills_ledger()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 231`** (2 nodes): `test_dashboard_watchlist.py`, `test_overview_api_contains_watchlist_rows()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 232`** (2 nodes): `test_sync_paper_state.py`, `test_build_positions_from_trades_aggregates_buys_and_sells()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 233`** (2 nodes): `test_layered_review_metadata.py`, `test_auto_post_review_cycle_persists_review_window_metadata()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 234`** (2 nodes): `test_dashboard_agent_response_lifecycle.py`, `test_overview_template_shows_agent_source_and_review_status()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 235`** (2 nodes): `test_fills_ledger_state_io.py`, `test_save_and_load_fills_ledger_roundtrip()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 236`** (2 nodes): `test_layered_review_schedule_plan.py`, `test_build_layered_review_schedule_plan_contains_windows_and_binding_fields()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 237`** (2 nodes): `test_dashboard_overview_template_filled_reconciliation.py`, `test_overview_template_mentions_filled_reconciliation_section()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 238`** (2 nodes): `test_dashboard_market_calendar_overview.py`, `test_overview_api_exposes_market_calendar_status_block()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 239`** (2 nodes): `test_dashboard_command.py`, `test_etf_tw_includes_dashboard_command()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 240`** (2 nodes): `test_layered_review_windows.py`, `test_get_layered_review_windows_returns_early_short_mid()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 241`** (2 nodes): `test_dashboard_position_view.py`, `test_build_position_view_includes_name_with_watchlist_or_etf_map()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 242`** (2 nodes): `test_dashboard_health_reconciliation_merge.py`, `test_overview_health_summary_includes_reconciliation_warnings_field()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 243`** (2 nodes): `test_sync_ohlcv_history_mapping.py`, `test_build_candidate_symbols_respects_mapping_registry()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 244`** (2 nodes): `test_sync_strategy_link.py`, `test_build_strategy_payload_maps_strategy_state()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 245`** (2 nodes): `test_partial_fill_fill_ledger_contract.py`, `test_partial_fill_event_row_contains_minimum_fill_facts()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 246`** (2 nodes): `test_broker_seq_precedence.py`, `test_higher_broker_seq_should_win_when_time_and_status_same()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 247`** (2 nodes): `test_dashboard_quality_hooks_panel.py`, `test_overview_template_shows_quality_hooks_summary()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 248`** (2 nodes): `sync_agent_evolution.py`, `sync_evolution()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 249`** (2 nodes): `check_orders.py`, `check()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 250`** (2 nodes): `verify_decision_engine_stability.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 251`** (2 nodes): `refresh_decision_engine_state.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 252`** (2 nodes): `update_experiment_decisions.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 253`** (2 nodes): `sync_news_from_rss.py`, `fetch_rss()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 254`** (2 nodes): `update_source_matrix.py`, `update_checked_date()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 255`** (2 nodes): `sync_family_ecosystem.py`, `sync_family()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 256`** (2 nodes): `notify_agent_mode_change.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 257`** (2 nodes): `sync_central_bank_calendar.py`, `sync_calendar()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 258`** (2 nodes): `sync_layered_review_status.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 259`** (2 nodes): `notify_agent_strategy_change.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 260`** (2 nodes): `layered_review_cron_draft.py`, `build_layered_review_cron_jobs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 261`** (2 nodes): `register_layered_review_jobs_via_setup.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 262`** (2 nodes): `translate_background.py`, `launch_job()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 263`** (2 nodes): `build_regime_bucket_stats.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 264`** (2 nodes): `refresh_monitoring_state.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 265`** (2 nodes): `review_auto_decisions.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 266`** (2 nodes): `venv_executor.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 267`** (2 nodes): `state_schema.py`, `validate_state_payload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 268`** (2 nodes): `[DOC] IDENTITY`, `[H1] IDENTITY.md`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 269`** (1 nodes): `diag_shioaji_vix.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 270`** (1 nodes): `diag_shioaji_contracts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 271`** (1 nodes): `sync_shioaji_data.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 272`** (1 nodes): `diag_probe.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 273`** (1 nodes): `Connect to the broker's API`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 274`** (1 nodes): `Get cash balance and purchasing power`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 275`** (1 nodes): `Get current stock/ETF holdings`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 276`** (1 nodes): `Place an order         action: 'BUY' or 'SELL'         order_type: 'MARKET' or '`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 277`** (1 nodes): `ETF 00878`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 278`** (1 nodes): `[CODE] from scripts.adapters.sinopac_adapter_enhanced import Sinopa...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 279`** (1 nodes): `[CODE] 參考價：76.2
漲停：83.8
跌停：68.6
有效：True
警告：[]...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 280`** (1 nodes): `[CODE] from scripts.adapters.base import Order

# 建立訂單
order = Orde...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 281`** (1 nodes): `[CODE] # 定義回調函數
def my_order_callback(api, order, status):
    prin...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 282`** (1 nodes): `[CODE] limits = await adapter.query_trade_limits()

if limits['can_...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 283`** (1 nodes): `[CODE] import asyncio
from scripts.adapters.sinopac_adapter_enhance...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 284`** (1 nodes): `[CODE] # 檢查漲停價
result = await adapter.check_price_limits('0050', 85...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 285`** (1 nodes): `[CODE] orders = [
    Order(symbol='0050', action='buy', quantity=1...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 286`** (1 nodes): `[CODE] # 建立虛擬環境
python -m venv .venv

# 激活虛擬環境 (Windows)
.venv\Scri...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 287`** (1 nodes): `[CODE] cd ETF_TW
ls -la
# 應包含：SKILL.md, scripts/, references/, data...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 288`** (1 nodes): `[CODE] # 此指令會自動檢查環境、安裝缺失套件、建立配置與帳本
python scripts/etf_tw.py init --...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 289`** (1 nodes): `[CODE] pip install yfinance pandas numpy shioaji...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 290`** (1 nodes): `[CODE] python scripts/etf_tw.py check --install-deps...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 291`** (1 nodes): `[CODE] python scripts/etf_tw.py check --install-deps...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 292`** (1 nodes): `[CODE] ETF_TW/
├── SKILL.md                    # 技能定義文件（OpenClaw 讀取...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 293`** (1 nodes): `[CODE] # 統一入口
python scripts/etf_tw.py query 0050
python scripts/et...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 294`** (1 nodes): `[CODE] cp assets/config.example.json assets/config.json...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 295`** (1 nodes): `[CODE] {
  "trading": {
    "default_mode": "paper",
    "default_b...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 296`** (1 nodes): `[CODE] python -m pip install -r scripts/etf_core/requirements.txt...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 297`** (1 nodes): `[CODE] yfinance>=0.2.0
pandas>=2.0.0
numpy>=1.24.0...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 298`** (1 nodes): `[CODE] python3 scripts/account_manager.py init --account paper_lab ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 299`** (1 nodes): `[CODE] python3 scripts/paper_trade.py init-holding --etf 0050 --sha...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 300`** (1 nodes): `[CODE] python3 scripts/etf_tw.py --check...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 301`** (1 nodes): `[CODE] ✓ Python 環境：OK
✓ 依賴套件：OK
✓ 資料庫連接：OK
✓ ETF 資料：OK
✓ 券商配置：OK...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 302`** (1 nodes): `[CODE] cd ~/.openclaw/skills/ETF_TW
git pull origin main
# 或
clawhu...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 303`** (1 nodes): `[CODE] python scripts/sync_strategy_link.py
python scripts/sync_pap...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 304`** (1 nodes): `[CODE] # 測試 1: 正常小額交易 (100 股)
有效：True
錯誤：[]
警告：[]  # ✅ 無警告，正常

# 測試...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 305`** (1 nodes): `[CODE] python scripts/etf_tw.py submit-preview --symbol 0050 --side...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 306`** (1 nodes): `[CODE] python scripts/etf_tw.py submit-preview --symbol 0050 --side...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 307`** (1 nodes): `[CODE] cd ~/.openclaw/skills/ETF_TW
git pull...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 308`** (1 nodes): `[CODE] python3 scripts/setup_agent.py --link etf_master...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 309`** (1 nodes): `[CODE] python3 scripts/setup_agent.py --new etf_pro_advisor...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 310`** (1 nodes): `[CODE] python3 scripts/setup_agent.py --list...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 311`** (1 nodes): `[CODE] .venv/bin/python scripts/sync_etf_universe_tw.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 312`** (1 nodes): `ETF 00679B`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 313`** (1 nodes): `[CODE] api = sj.Shioaji(simulation=True)  # 模擬環境
api = sj.Shioaji(s...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 314`** (1 nodes): `[CODE] balance = api.account_balance(stock_acc)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 315`** (1 nodes): `[CODE] positions = api.list_positions(stock_acc)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 316`** (1 nodes): `[CODE] contract = api.Contracts.Stocks.TSE['0050']...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 317`** (1 nodes): `[CODE] trades = api.list_trades()...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 318`** (1 nodes): `[CODE] from shioaji.constant import Action, OrderType, StockPriceTy...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 319`** (1 nodes): `[CODE] ETF_TW/
├── SKILL.md
├── TASKS.md
├── INSTALL.md
├── README....`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 320`** (1 nodes): `[CODE] # 計算 Python 腳本數量
find scripts -name "*.py" -not -path "*/__p...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 321`** (1 nodes): `[CODE] ETF_TW/
├── SKILL.md                    # 本文件
├── data/
│   ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 322`** (1 nodes): `[CODE] 2. **環境點檢**：...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 323`** (1 nodes): `[CODE] 3. **自動初始化**：...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 324`** (1 nodes): `[CODE] 4. **查看資產回報** (老手常用)：...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 325`** (1 nodes): `[CODE] *此指令會計算實現/未實現損益與總報酬。*
   *此指令會自動補齊缺失套件、建立 `assets/config.jso...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 326`** (1 nodes): `[CODE] ### 2. 重要規範
- **帳戶別名**：應與 `trading_mode.json` 中的 `default_ac...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 327`** (1 nodes): `[CODE] 並將輸出的口語範例呈現給用戶，引導用戶開始互動。

---

## 操作指引

### 當使用者需要 ETF 基本資料
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 328`** (1 nodes): `[CODE] ---

## Decision Provenance Logger（決策溯源記錄器）

### 核心概念
每次決策（p...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 329`** (1 nodes): `[CODE] **F1 已修復**：POST `/api/auto-trade/submit` 端點（4道Gate確認機制）
- Ga...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 330`** (1 nodes): `[CODE] **mode 標記**：
- Tier 1 → `mode: "preview-only"`（正常）
- Tier 2 ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 331`** (1 nodes): `[CODE] **資料來源**（唯讀、不改原始格式）：
- `decision_log.jsonl` — 決策掃描紀錄
- `auto...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 332`** (1 nodes): `[CODE] **CLI 使用**：...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 333`** (1 nodes): `[CODE] **Dashboard API**：
- `GET /api/trade-journal` — 列出所有可用歸檔日期
-...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 334`** (1 nodes): `[CODE] **2. 重大事件偵測**...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 335`** (1 nodes): `[CODE] **3. 決策引擎刷新**...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 336`** (1 nodes): `[CODE] **4. Wiki 知識更新（判讀層）**

注意：State 檔案名稱對照
- 重大事件觸發檔案：`major_eve...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 337`** (1 nodes): `ETF 00929`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 338`** (1 nodes): `ETF 00892`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 339`** (1 nodes): `ETF 00923`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 340`** (1 nodes): `[CODE] python scripts/etf_tw.py init --install-deps...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 341`** (1 nodes): `[CODE] python scripts/etf_tw.py check...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 342`** (1 nodes): `[CODE] python scripts/etf_tw.py list
  python scripts/etf_tw.py sea...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 343`** (1 nodes): `[CODE] python scripts/etf_tw.py compare 0050 006208...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 344`** (1 nodes): `[CODE] python scripts/etf_tw.py calc 0050 10000 10 --annual-return ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 345`** (1 nodes): `[CODE] python scripts/etf_tw.py portfolio...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 346`** (1 nodes): `[CODE] python scripts/etf_tw.py paper-trade --symbol 0050 --side bu...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 347`** (1 nodes): `[CODE] bash scripts/start_dashboard.sh...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 348`** (1 nodes): `[CODE] cd ~/.openclaw/skills/ETF_TW && .venv/bin/python3 -m uvicorn...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 349`** (1 nodes): `[CODE] validate → preview → confirm → execute...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 350`** (1 nodes): `[CODE] 使用者：買進 0050 100 股

Validate 結果：
✅ 標的有效：0050.TW
✅ 數量合理：100 股
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 351`** (1 nodes): `[CODE] 使用者：買進 0050 100 股 @ 75 元

Preview 結果：
┌─────────────────────...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 352`** (1 nodes): `[CODE] ✅ 買進成功！
0050 x 100 股 @ 75.00 元

持倉更新：
- 0050: 100 股（平均成本 75....`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 353`** (1 nodes): `[CODE] ⚠️ 單位混淆警告！

您輸入：400 張 0050 = 40,000 股
目前帳戶總值：約 25,000 元
單筆交易...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 354`** (1 nodes): `[CODE] ⚠️ 大額交易警告！

單筆交易價值：1,500,000 元
目前總持倉：2,000,000 元
占比：75%（超過 5...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 355`** (1 nodes): `[CODE] ⚠️ 訊號衝突！

技術面：
- RSI: 28（超賣，買進訊號）
- MA20: 股價跌破（賣出訊號）

基本面：
-...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 356`** (1 nodes): `[CODE] ## 交易紀錄

| 日期 | 時間 | 標的 | 動作 | 價格 | 股數 | 金額 | 手續費 | 備註 |
|--...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 357`** (1 nodes): `[CODE] ## 當前持倉摘要（截至 2026-03-17 23:49）

| 標的 | 總股數 | 平均成本 | 當前價格 | 未...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 358`** (1 nodes): `[CODE] ❌ 驗證失敗

原因：現金不足
需要：7,510.69 元
目前：5,000 元

請增加現金或減少交易數量...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 359`** (1 nodes): `[CODE] ⚠️ 資料提示：
- 股價為 2026-03-23 收盤價
- 非即時報價
- 實際成交價可能不同...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 360`** (1 nodes): `[CODE] ⚠️ 免責聲明：
- 技術指標僅供參考
- 不構成投資建議
- 過去表現不代表未來...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 361`** (1 nodes): `[CODE] ⚠️ 資料限制：
- 該 ETF 費用率資料缺失
- 無法取得最新配息紀錄
- 建議交叉驗證其他來源...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 362`** (1 nodes): `[CODE] ## Data Update Log (YYYY-MM-DD)
- **標的**: [ETF 代號]
- **更新項目*...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 363`** (1 nodes): `[CODE] ## Data Update Log (2026-03-23)
- **標的**: 0050, 006208
- **更...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 364`** (1 nodes): `[CODE] 關鍵問題：什麼叫「自主判斷」？

目前架構：
ETF_master → 讀取 market cache → 決定買什麼 ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 365`** (1 nodes): `[CODE] 目前的風控：
- 交易時段檢查 ✅
- Pre-flight 檢查 ✅
- 風控規則（集中度、單位混淆）✅

但缺少：
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 366`** (1 nodes): `[CODE] 現有層級（推測）：
├── 記錄預測與實際結果
├── 計算準確率
└── 人類可查看報告

缺少層級：
❌ 自動調整決...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 367`** (1 nodes): `[CODE] 目前問題：
- 需要手動讓 ETF_master「跑測、修改斷掉的鏈路」
- state 檔案（如 auto_submi...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 368`** (1 nodes): `[CODE] 關鍵問題：什麼是「利潤最大化」？

風險：
❌ 如果目標函數只是「報酬率」，Agent 可能過度冒險
❌ 如果沒有考慮「...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 369`** (1 nodes): `[CODE] 目前：記錄 → 人類查看
應該：記錄 → 分析 → 自動調整參數 → 驗證效果 → 沉澱知識

具體行動：
1. 建立 ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 370`** (1 nodes): `[CODE] 目前：單筆風控、交易時段檢查
應該：組合風控、回撤限制、市場異常偵測

具體行動：
1. 建立「每日虧損上限」→ 觸發後...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 371`** (1 nodes): `[CODE] 目前：需要人類維護鏈路、修復 state
應該：自動健康檢查、自動修復、自動通知

具體行動：
1. 建立「健康檢查」c...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 372`** (1 nodes): `[CODE] from adapters import get_adapter
from trade_logger import ge...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 373`** (1 nodes): `[CODE] ETF_TW/
├── scripts/
│   ├── adapters/
│   │   ├── base.py
│...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 374`** (1 nodes): `[CODE] from scripts.trade_logger import get_logger

logger = get_lo...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 375`** (1 nodes): `[CODE] from scripts.risk_controller import get_risk_controller

ris...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 376`** (1 nodes): `[CODE] summary = risk_ctrl.get_daily_summary()
print(f"今日訂單數：{summa...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 377`** (1 nodes): `[CODE] # 查詢交易日誌
python3 scripts/etf_tw.py trade-logs --symbol 0050....`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 378`** (1 nodes): `[CODE] # 正式送單必須透過 venv_executor
python scripts/venv_executor.py com...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 379`** (1 nodes): `[CODE] # P2: 明確記錄 - 此掃描不影響送單狀態
print(f"[STATE] auto_trade_state 已更新...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 380`** (1 nodes): `[CODE] # 執行狀態對帳
python scripts/state_reconciliation_enhanced.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 381`** (1 nodes): `[CODE] ============================================================...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 382`** (1 nodes): `[CODE] # complete_trade.py 第 123-129 行
if mode in ('live', 'sandbox...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 383`** (1 nodes): `[CODE] cd skills/ETF_TW
python tests/test_venv_executor.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 384`** (1 nodes): `[CODE] ============================================================...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 385`** (1 nodes): `[CODE] instances/
├── etf_master/
│   └── state/
│       ├── orders...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 386`** (1 nodes): `[CODE] commit 099f23a
feat(ETF_TW): 修復正式單變預演與訂單消失問題 (P1-P3)

- P1: ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 387`** (1 nodes): `[CODE] commit e1414f6
test(ETF_TW): 加入 P4-P5 驗證測試

- P4: 交易時段硬閘門測試
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 388`** (1 nodes): `[CODE] # 1. 確認在交易時段
python scripts/venv_executor.py trading_hours_g...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 389`** (1 nodes): `[CODE] # 執行完整測試
python tests/test_venv_executor.py

# 檢查健康狀態
python...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 390`** (1 nodes): `[CODE] 測試 1：券商註冊表 ✅
測試 2：帳戶配置 ✅
測試 3：適配器實例化 ✅
測試 4：模擬交易完整流程 ✅...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 391`** (1 nodes): `[CODE] python3 scripts/etf_tw.py brokers...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 392`** (1 nodes): `[CODE] python3 scripts/etf_tw.py accounts...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 393`** (1 nodes): `[CODE] python3 scripts/etf_tw.py paper-account orders.json -a defau...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 394`** (1 nodes): `[CODE] python3 scripts/test_phase4.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 395`** (1 nodes): `[CODE] ## Incident Log (YYYY-MM-DD)
- **Event**: [事件描述]
- **Failure...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 396`** (1 nodes): `[CODE] ## Incident Log (2026-03-17)
- **Event**: 使用者請求「400 張 0050」（...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 397`** (1 nodes): `[CODE] skills/ETF_TW/.venv/bin/python   # 必須用 project venv...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 398`** (1 nodes): `[CODE] contract = api.Contracts.Stocks.TSE.TSE00878           # TSE...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 399`** (1 nodes): `[CODE] order = api.Order(
    price=27.25,
    quantity=100,       ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 400`** (1 nodes): `[CODE] trade = api.place_order(contract, order)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 401`** (1 nodes): `[CODE] api.update_status(api.stock_account)
# 確認：status 非 Failed/In...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 402`** (1 nodes): `[CODE] api.update_status(api.stock_account)
trades = api.list_trade...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 403`** (1 nodes): `[CODE] quantity=1,                                    # 張（1000股）
or...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 404`** (1 nodes): `[CODE] api.update_order(trade=trade, price=new_price)
api.update_or...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 405`** (1 nodes): `[CODE] positions = api.list_positions(api.stock_account)
balance = ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 406`** (1 nodes): `[CODE] Account:    9A9L / 0737121
Venv:       skills/ETF_TW/.venv/b...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 407`** (1 nodes): `ETF 00713`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 408`** (1 nodes): `ETF 00881`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 409`** (1 nodes): `ETF 00637L`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 410`** (1 nodes): `[CODE] snapshots = api.snapshots([api.Contracts.Stocks["2330"]])...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 411`** (1 nodes): `[CODE] ticks = api.ticks(api.Contracts.Stocks["2330"], date="2026-0...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 412`** (1 nodes): `[CODE] kbars = api.kbars(api.Contracts.Stocks["2330"], start="2026-...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 413`** (1 nodes): `[CODE] api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="Y...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 414`** (1 nodes): `[CODE] api = sj.Shioaji(simulation=True)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 415`** (1 nodes): `[CODE] api = sj.Shioaji()
api.login(api_key="YOUR_KEY", secret_key=...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 416`** (1 nodes): `[CODE] api.activate_ca(ca_path="/path/to/Sinopac.pfx", ca_passwd="Y...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 417`** (1 nodes): `[CODE] curl -LsSf https://astral.sh/uv/install.sh | sh
uv init my-t...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 418`** (1 nodes): `[CODE] 🚀 Phase 4 - 多券商架構測試

測試 1：券商註冊表
已載入 4 個券商：
  - sinopac: 永豐金證...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 419`** (1 nodes): `[CODE] ETF_TW/
├── data/
│   ├── broker_registry.json (NEW)
│   └──...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 420`** (1 nodes): `[CODE] python3 scripts/etf_tw.py accounts...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 421`** (1 nodes): `[CODE] python3 scripts/etf_tw.py brokers...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 422`** (1 nodes): `[CODE] python3 scripts/etf_tw.py preview-account orders.json -a my_...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 423`** (1 nodes): `[CODE] python3 scripts/etf_tw.py paper-account orders.json -a defau...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 424`** (1 nodes): `[CODE] python3 scripts/test_phase4.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 425`** (1 nodes): `[CODE] # 列出 ETF
python3 scripts/etf_tw.py list

# 搜尋
python3 script...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 426`** (1 nodes): `[CODE] # 模擬交易（預設）
python3 scripts/complete_trade.py 0050.TW buy 100...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 427`** (1 nodes): `[CODE] # 查詢日志
python3 scripts/etf_tw.py trade-logs --symbol 0050.TW...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 428`** (1 nodes): `[CODE] 測試：永豐金證券適配器（Scaffold）
=====================================
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 429`** (1 nodes): `[CODE] async def authenticate(self) -> bool:
    # TODO: 實作真實的永豐金 A...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 430`** (1 nodes): `[CODE] async def get_market_data(self, symbol: str) -> Dict:
    # ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 431`** (1 nodes): `[CODE] async def submit_order(self, order: Order) -> Order:
    # T...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 432`** (1 nodes): `[CODE] # 範例：使用 aiohttp 進行非同步 API 調用
async def _call_api(self, endpo...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 433`** (1 nodes): `[CODE] ETF_TW/
├── scripts/
│   ├── adapters/
│   │   ├── base.py (...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 434`** (1 nodes): `[CODE] from adapters.sinopac_adapter import create_sinopac_adapter
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 435`** (1 nodes): `[CODE] python3 scripts/test_sinopac.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 436`** (1 nodes): `[CODE] # 使用永豐金帳戶進行模擬交易
python3 scripts/etf_tw.py paper-account orde...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 437`** (1 nodes): `[CODE] {
  "kind": "every",
  "everyMs": 86400000
}...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 438`** (1 nodes): `[CODE] python3 scripts/run_etf_tw_task.py auto_post_review_cycle <s...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 439`** (1 nodes): `[CODE] python3 scripts/setup_agent.py --link <instance_id> --init-c...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 440`** (1 nodes): `[CODE] python3 scripts/register_standard_cron_pack.py <instance_id>...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 441`** (1 nodes): `[CODE] python3 scripts/register_standard_cron_pack.py <instance_id>...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 442`** (1 nodes): `[CODE] ETF_TW/instances/<agent_id>/state/...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 443`** (1 nodes): `[CODE] /Users/tuchengshin/.openclaw/skills/ETF_TW/instances/etf_mas...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 444`** (1 nodes): `[CODE] ETF_TW/state/...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 445`** (1 nodes): `[CODE] (1) sync_strategy_link.py
(2) sync_live_state.py / sync_pape...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 446`** (1 nodes): `[CODE] 【策略：{base_strategy}｜覆蓋：{scenario_overlay}】...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 447`** (1 nodes): `ETF 00922`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 448`** (1 nodes): `[CODE] import shioaji as sj
api = sj.Shioaji()
api.login(
    api_k...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 449`** (1 nodes): `[CODE] api = sj.Shioaji()
api.login(
    person_id="YOUR_PERSON_ID"...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 450`** (1 nodes): `[CODE] api.login(
    api_key="KEY", secret_key="SECRET",
    contr...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 451`** (1 nodes): `[CODE] accounts = api.list_accounts()
# [StockAccount(...), FutureA...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 452`** (1 nodes): `[CODE] api.subscribe_trade(account)
api.unsubscribe_trade(account)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 453`** (1 nodes): `[CODE] api.logout()  # → True (注意：會觸發 segfault exit 139，見已知問題)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 454`** (1 nodes): `[CODE] # 不在登入時自動載入
api.login(api_key="KEY", secret_key="SECRET", fe...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 455`** (1 nodes): `[CODE] api.login(api_key="KEY", secret_key="SECRET", contracts_time...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 456`** (1 nodes): `[CODE] # 方式一：代碼直接查
api.Contracts.Stocks["2890"]

# 方式二：交易所+代碼
api.C...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 457`** (1 nodes): `[CODE] api.Contracts.Futures["TXFA3"]
api.Contracts.Futures.TXF.TXF...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 458`** (1 nodes): `[CODE] api.Contracts.Indexs.TSE["001"]
# Index(exchange=TSE, code='...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 459`** (1 nodes): `[CODE] contract = api.Contracts.Stocks.TSE.TSE2890

order = api.Ord...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 460`** (1 nodes): `[CODE] api.place_order(
    contract: shioaji.contracts.Contract,
 ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 461`** (1 nodes): `[CODE] Trade(
    contract=Stock(...),
    order=Order(
        act...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 462`** (1 nodes): `[CODE] # 現股買進
action=sj.constant.Action.Buy
order_lot=sj.constant.S...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 463`** (1 nodes): `[CODE] contract = api.Contracts.Stocks.TSE.TSE0050

order = api.Ord...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 464`** (1 nodes): `[CODE] api.update_status(api.stock_account)
trades = api.list_trade...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 465`** (1 nodes): `[CODE] api.update_status(
    account: Account = None,
    trade: T...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 466`** (1 nodes): `[CODE] api.update_order(trade=trade, price=17.5)
api.update_status(...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 467`** (1 nodes): `[CODE] api.update_order(trade=trade, qty=1)
api.update_status(api.s...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 468`** (1 nodes): `[CODE] api.update_order(
    trade: Trade,
    price: Union[int, fl...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 469`** (1 nodes): `[CODE] api.cancel_order(trade)
api.update_status(api.stock_account)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 470`** (1 nodes): `[CODE] Deal(seq='000001', price=17, quantity=3, ts=1673501631.62918...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 471`** (1 nodes): `[CODE] api.list_positions(api.stock_account)

# 回傳:
# [
#   Positio...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 472`** (1 nodes): `[CODE] api.list_positions(
    account: Account = None,
    unit: U...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 473`** (1 nodes): `[CODE] api.account_balance()
api.account_balance(account=api.stock_...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 474`** (1 nodes): `[CODE] api.account_balance(
    account: Account = None,
    timeou...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 475`** (1 nodes): `[CODE] profitloss = api.list_profit_loss(
    api.stock_account,
  ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 476`** (1 nodes): `[CODE] api.list_profit_loss(
    account: Account = None,
    begin...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 477`** (1 nodes): `[CODE] detail = api.list_profit_loss_detail(
    api.stock_account,...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 478`** (1 nodes): `[CODE] summary = api.list_profit_loss_summary(
    api.stock_accoun...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 479`** (1 nodes): `[CODE] api.margin(api.futopt_account)
# Margin(yesterday_balance=60...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 480`** (1 nodes): `[CODE] settlements = api.settlements(api.stock_account)

# [
#   Se...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 481`** (1 nodes): `[CODE] api.settlements(
    account: Account = None,
    timeout: i...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 482`** (1 nodes): `[CODE] api.trading_limits(api.stock_account)

# TradingLimits(
#   ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 483`** (1 nodes): `[CODE] @api.quote.on_event
def event_callback(resp_code: int, event...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 484`** (1 nodes): `[CODE] def order_cb(stat, msg):
    print('my_order_callback')
    ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 485`** (1 nodes): `[CODE] {
    'operation': {
        'op_type': 'New',          # Ne...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 486`** (1 nodes): `[CODE] {
    'trade_id': '9c6ae2eb',
    'seqno': '269866',
    'or...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 487`** (1 nodes): `[CODE] # 漲停價
limit_up = api.calc_limit_up_price(
    price=contract...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 488`** (1 nodes): `[CODE] contracts = [api.Contracts.Stocks['2330'], api.Contracts.Sto...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 489`** (1 nodes): `[CODE] api.snapshots(
    contracts: List[Contract],
    timeout: i...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 490`** (1 nodes): `[CODE] import pandas as pd
df = pd.DataFrame(s.__dict__ for s in sn...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 491`** (1 nodes): `[CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 492`** (1 nodes): `[CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 493`** (1 nodes): `[CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 494`** (1 nodes): `[CODE] api.quote.subscribe(
    contract: Contract,
    quote_type:...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 495`** (1 nodes): `[CODE] api.quote.subscribe(
    contract,
    quote_type=sj.constan...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 496`** (1 nodes): `[CODE] api.quote.unsubscribe(contract, sj.constant.QuoteType.Tick, ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 497`** (1 nodes): `[CODE] from shioaji import TickSTKv1, Exchange

def quote_callback(...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 498`** (1 nodes): `[CODE] from shioaji import BidAskSTKv1, Exchange

def bidask_callba...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 499`** (1 nodes): `[CODE] # 事件回呼（訂閱成功/失敗）
api.quote.set_event_callback(func)

# Tick v...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 500`** (1 nodes): `[CODE] ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"]...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 501`** (1 nodes): `[CODE] api.ticks(
    contract: BaseContract,
    date: str = '2022...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 502`** (1 nodes): `[CODE] ticks = api.ticks(
    contract=api.Contracts.Stocks["2330"]...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 503`** (1 nodes): `[CODE] kbars = api.kbars(
    contract=api.Contracts.Stocks["2330"]...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 504`** (1 nodes): `[CODE] api.kbars(
    contract: BaseContract,
    start: str = '202...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 505`** (1 nodes): `[CODE] import pandas as pd

df = pd.DataFrame({**kbars})
df.ts = pd...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 506`** (1 nodes): `[CODE] trade = api.place_order(contract, order, timeout=0)
# status...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 507`** (1 nodes): `[CODE] api.update_status(api.stock_account, timeout=0)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 508`** (1 nodes): `[CODE] api.cancel_order(trade, timeout=0)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 509`** (1 nodes): `[CODE] import shioaji as sj

api = sj.Shioaji(simulation=True)
acco...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 510`** (1 nodes): `[CODE] import shioaji as sj

# 1. 初始化
api = sj.Shioaji()

# 2. 登入
a...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 511`** (1 nodes): `[CODE] # 1. 取得合約（注意 OTC 用 .get()）
contract = api.Contracts.Stocks.O...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 512`** (1 nodes): `[CODE] import shioaji as sj

# Action
sj.constant.Action.Buy
sj.con...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 513`** (1 nodes): `[CODE] {
  "request_id": "string",
  "generated_at": "ISO timestamp...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 514`** (1 nodes): `[CODE] {
  "request_id": "string",
  "created_at": "ISO timestamp",...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 515`** (1 nodes): `[CODE] {
  "request_id": "string",
  "generated_at": "ISO timestamp...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 516`** (1 nodes): `[CODE] python simulator.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 517`** (1 nodes): `[CODE] python main_service.py...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 518`** (1 nodes): `[CODE] from main_service import ETF_TW_Pro

service = ETF_TW_Pro()
...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 519`** (1 nodes): `[CODE] result = service.execute_buy('0050.TW', 100)
print(result)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 520`** (1 nodes): `[CODE] report = service.get_portfolio_report()
print(report)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 521`** (1 nodes): `[CODE] 名稱：YUANTA SECURITIES INV TRUST CO
目前價：75.75
昨收：78.75
漲跌：-3.0...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 522`** (1 nodes): `[CODE] 1. [Yahoo 財經] 傳承 281 年土地公福氣 竹山紫南宮呷平安丁酒萬人空巷...
   時間：Wed, 04 ...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 523`** (1 nodes): `[CODE] 初始現金：1,000,000
總資產：1,000,000...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 524`** (1 nodes): `[CODE] 結果：✅ 買進成功！
成交金額：7,510.69 (含手續費)
買進後現金：992,489
持倉總值：7,580...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 525`** (1 nodes): `[CODE] 0050.TW: 100 股
  均價：75.00
  現價：75.80
  損益：+80.00 (+1.07%)...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 526`** (1 nodes): `[CODE] 市場狀態：盤中
0050.TW: 75.75 (0.00%) - 信號：跌破 MA20
006208.TW: 175.6...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 527`** (1 nodes): `[CODE] 現金：992,489
總資產：1,000,069
損益：+69 (+0.01%)

持倉明細:
  0050.TW: 1...`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Order` connect `Community 1` to `Community 0`, `Community 3`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `BaseAdapter` connect `Community 0` to `Community 1`, `Community 10`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Why does `Execute a complete trade with risk control and logging.      Args:         symbo` connect `Community 3` to `Community 1`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 88 inferred relationships involving `Order` (e.g. with `Test Cathay adapter scaffold.` and `Test Yuanlin adapter scaffold.`) actually correct?**
  _`Order` has 88 INFERRED edges - model-reasoned connections that need verification._
- **Are the 78 inferred relationships involving `BaseAdapter` (e.g. with `AccountManager` and `Manages multiple trading accounts across different brokers.          Features:`) actually correct?**
  _`BaseAdapter` has 78 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `Position` (e.g. with `SinopacAdapter` and `SinoPac Securities (Shioaji) adapter.     包含漲跌停檢查與完整訂單驗證`) actually correct?**
  _`Position` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `AccountBalance` (e.g. with `SinopacAdapter` and `SinoPac Securities (Shioaji) adapter.     包含漲跌停檢查與完整訂單驗證`) actually correct?**
  _`AccountBalance` has 57 INFERRED edges - model-reasoned connections that need verification._