# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** Event-driven state machine with multi-layer truth architecture and dual decision consensus

**Key Characteristics:**
- Instance state as single source of truth (multi-tenant isolation)
- File-based JSON/JSONL state with atomic writes
- Broker adapter pattern (Strategy pattern) for multi-broker support
- Staged autonomy: rule engine + AI bridge with tiered consensus arbitration
- Sequential refresh pipeline with strict ordering
- 4-layer precedence model for broker order reconciliation
- Separation of truth layer (positions/orders) from display layer (summaries)

## Layers

**Presentation Layer (Dashboard):**
- Purpose: Web UI for portfolio, orders, AI suggestions, health monitoring
- Location: `skills/ETF_TW/dashboard/`
- Contains: FastAPI app, Jinja2 templates, API endpoints
- Depends on: Instance state files (read-only), `etf_core/context.py`, reconciliation helpers
- Used by: Human operator via browser (port 5055)

**Decision Layer (AI Bridge + Rule Engine):**
- Purpose: Generate trading decisions from market data and portfolio state
- Location: `skills/ETF_TW/scripts/ai_decision_bridge.py`, `scripts/run_auto_decision_scan.py`, `scripts/generate_ai_decision_response.py`, `scripts/generate_ai_agent_response.py`
- Contains: Request/Response builders, consensus resolver, provenance logger
- Depends on: Refresh pipeline outputs (all state files)
- Used by: Dashboard (displays suggestions), Cron jobs (triggers scans)

**Orchestration Layer (Refresh Pipeline):**
- Purpose: Sequentially sync and enrich state from external data sources
- Location: `skills/ETF_TW/scripts/sync_*.py`, `scripts/generate_*.py`, `scripts/check_major_event_trigger.py`
- Contains: 10 ordered scripts that build the complete market/policy picture
- Depends on: Shioaji API, yfinance, instance config, broker adapters
- Used by: Cron jobs, manual triggers, dashboard refresh API

**Execution Layer (Trading):**
- Purpose: Validate, preview, and submit orders through broker adapters
- Location: `skills/ETF_TW/scripts/complete_trade.py`, `scripts/preview_order.py`, `scripts/validate_order.py`, `scripts/risk_controller.py`
- Contains: Order lifecycle, trading hours gate, venv executor, fee/tax calculation
- Depends on: Broker adapters, risk controller, trading mode state
- Used by: Agent commands, auto-trade scan (paper mode)

**Adapter Layer (Broker Abstraction):**
- Purpose: Abstract broker-specific APIs behind a common interface
- Location: `skills/ETF_TW/scripts/adapters/base.py`, `scripts/adapters/paper_adapter.py`, `scripts/adapters/sinopac_adapter.py`, `scripts/adapters/cathay_adapter.py`, `scripts/adapters/yuanlin_adapter.py`
- Contains: `BaseAdapter` ABC with `Order`, `Position`, `AccountBalance` dataclasses; `get_adapter()` factory
- Depends on: shioaji SDK (sinopac), yfinance (market data fallback)
- Used by: `account_manager.py`, `complete_trade.py`, `sync_live_state.py`

**State Layer (Persistence):**
- Purpose: Single source of truth for all runtime data
- Location: `skills/ETF_TW/instances/<agent_id>/state/` (e.g., `instances/etf_master/state/`)
- Contains: 27+ JSON and JSONL files; append-only journals, atomic-overwrite snapshots
- Depends on: Nothing (root truth layer)
- Used by: All layers above (read); refresh pipeline and execution layer (write)

**Core Utility Layer:**
- Purpose: Shared infrastructure for state I/O, schema validation, path resolution
- Location: `skills/ETF_TW/scripts/etf_core/context.py`, `scripts/etf_core/state_io.py`, `scripts/etf_core/state_schema.py`
- Contains: `get_state_dir()`, `get_instance_dir()`, `safe_load_json()`, `atomic_save_json()`, `safe_append_jsonl()`, `validate_state_payload()`
- Depends on: `AGENT_ID` / `OPENCLAW_AGENT_NAME` env vars
- Used by: Every script in the project

## Data Flow

**Trading Decision Flow:**

1. Cron triggers `sync_market_cache.py` -- fetches quotes via yfinance
2. `sync_live_state.py` / `sync_paper_state.py` -- syncs positions from broker or paper ledger
3. `sync_market_cache.py` -- updates `market_cache.json` and `market_intelligence.json`
4. `generate_market_event_context.py` -- derives `market_event_context.json` from intelligence
5. `generate_taiwan_market_context.py` -- derives `market_context_taiwan.json` from intelligence + event context
6. `check_major_event_trigger.py` -- writes `major_event_flag.json`
7. `sync_portfolio_snapshot.py` -- aggregates positions + cash into `portfolio_snapshot.json`
8. `sync_ohlcv_history.py` -- enriches `market_intelligence.json` with RSI/MACD/SMA
9. `generate_intraday_tape_context.py` -- generates `intraday_tape_context.json`
10. `sync_agent_summary.py` -- composes `agent_summary.json` from all above

**Auto Decision Scan Flow:**

1. `run_auto_decision_scan.py` checks strategy, positions, market context
2. Rule engine evaluates conditions and produces `rule_engine_action`
3. AI bridge: `generate_ai_decision_request.py` builds `ai_decision_request.json`
4. AI agent reads request, generates response via `generate_ai_decision_response.py`
5. `generate_ai_agent_response.py` builds agent-consumed response
6. `resolve_consensus()` merges rule engine + AI bridge decisions (Tier 1/2/3)
7. Result written to `auto_preview_candidate.json`
8. Provenance logged to `decision_provenance.jsonl`

**Order Execution Flow:**

1. Agent or user requests trade via CLI or dashboard
2. `trading_hours_gate.py` checks if market is open (09:00-13:30 or 13:40-14:30)
3. `risk_controller.py` validates position limits, order size, duplicates
4. `validate_order.py` performs additional checks (concentration, unit confusion)
5. `preview_order.py` generates preview without submission
6. User approves (explicit confirmation required for live)
7. `complete_trade.py` dispatches to broker adapter via `account_manager.py`
8. Adapter submits order, returns `Order` result
9. `orders_open_state.py` writes to `orders_open.json`
10. `trade_logger.py` logs to `data/trade_logs.jsonl`
11. `submit_verification.py` verifies with `list_trades()`
12. `poll_order_status.py` monitors status changes
13. `order_event_bridge.py` normalizes callback/polling events
14. `order_event_precedence.py` resolves conflicts (4-layer precedence)
15. `fills_ledger.py` records fill facts
16. `state_reconciliation_enhanced.py` reconciles orders/positions/fills

**State Management:**
- **JSON files**: Atomic overwrite via `atomic_save_json()` (write temp + rename)
- **JSONL files**: Append-only via `safe_append_jsonl()` (audit trail -- decisions, provenance, outcomes)
- **Schema validation**: `validate_state_payload()` checks required keys per state kind
- **Downstream protection**: Display summaries (`agent_summary.json`, `intraday_tape_context.json`) MUST NOT overwrite truth files (`positions.json`, `orders_open.json`, `account_snapshot.json`)

## Key Abstractions

**BaseAdapter (Broker Adapter Pattern):**
- Purpose: Abstract all broker-specific APIs behind a uniform interface
- Examples: `scripts/adapters/base.py` (BaseAdapter), `scripts/adapters/sinopac_adapter.py` (SinopacAdapter), `scripts/adapters/paper_adapter.py` (PaperAdapter)
- Pattern: Strategy pattern with ABC; `get_adapter()` factory dispatches by `broker_id`; new brokers subclass BaseAdapter, implement 7 abstract methods (`authenticate`, `get_market_data`, `get_account_balance`, `get_positions`, `preview_order`, `validate_order`, `submit_order`, `cancel_order`, `get_order_status`)

**Order Event Precedence:**
- Purpose: Resolve conflicts when multiple sources update the same order
- Examples: `scripts/order_event_precedence.py` (`choose_preferred_row()`), `scripts/order_event_bridge.py` (`event_payload_to_order_row()`)
- Pattern: 4-layer deterministic comparison: (1) status rank (terminal states cannot be overwritten), (2) timestamp precedence (`event_time` > `observed_at`), (3) `broker_seq` (higher wins), (4) source priority (callback=4 > polling=3 > verification=2 > response=1 > inference=0)

**Dual Decision Consensus:**
- Purpose: Merge deterministic rule engine with probabilistic AI bridge
- Examples: `scripts/run_auto_decision_scan.py` (`resolve_consensus()`)
- Pattern: Three-tier arbitration: Tier 1 (both agree on symbol + direction = high confidence, execute), Tier 2 (disagreement = rule engine has veto, medium confidence), Tier 3 (opposite directions on same symbol = locked, requires human)

**Provenance Logger:**
- Purpose: Append-only audit trail for every decision cycle
- Examples: `scripts/provenance_logger.py` (`build_provenance_record()`, `append_provenance()`)
- Pattern: One JSONL record per decision with `inputs_digest` (compressed market context), `outputs` (action/symbol/confidence), and `review_lifecycle` (T1/T3/T10 back-fill slots); records are never deleted or overwritten

**AI Decision Bridge State Contract:**
- Purpose: Formal request/response protocol between dashboard/scripts and AI agent
- Examples: `scripts/ai_decision_bridge.py` (`build_ai_decision_request()`, `build_ai_decision_response()`, `is_ai_decision_response_stale()`)
- Pattern: Request artifact (`ai_decision_request.json`) aggregates 12 input sources; Response artifact (`ai_decision_response.json`) includes `expires_at`, `stale` flag, `confidence`, `uncertainty`, `strategy_alignment`, and `input_refs` for traceability; freshness tracked via ISO timestamps with `Asia/Taipei` timezone

**Context Hub (Multi-Instance Routing):**
- Purpose: Route all path resolution through instance-aware functions
- Examples: `scripts/etf_core/context.py` (`get_instance_id()`, `get_state_dir()`, `get_instance_dir()`, `get_instance_config()`, `get_broker_config()`)
- Pattern: All state paths derived from `AGENT_ID` env var; auto-creates directory structure; singleton warning for missing env var

## Entry Points

**CLI Entry Point:**
- Location: `skills/ETF_TW/scripts/etf_tw.py`
- Triggers: Hermes agent commands, shell invocation via `.venv/bin/python3 scripts/etf_tw.py <command>`
- Responsibilities: ETF list/search/filter, comparison, DCA calculation, order preview/validation/paper trading, multi-broker account management

**Dashboard Entry Point:**
- Location: `skills/ETF_TW/dashboard/app.py`
- Triggers: `.venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055`
- Responsibilities: FastAPI web server; strategy update API, auto-trade config API, order submission API, health monitoring, reconciliation alerts, refresh triggers

**Venv Executor:**
- Location: `skills/ETF_TW/scripts/venv_executor.py`
- Triggers: Hermes agent executing scripts from possibly wrong Python environment
- Responsibilities: Forces all script execution through `.venv/bin/python3` to prevent "live order from wrong env" incidents

**Auto Decision Scan:**
- Location: `skills/ETF_TW/scripts/run_auto_decision_scan.py`
- Triggers: Cron jobs (`ETF 早班準備`, `ETF 健康巡檢`), manual invocation
- Responsibilities: Runs rule engine evaluation + AI bridge consensus, writes preview candidates, logs provenance

**Refresh Pipeline Scripts:**
- Location: `skills/ETF_TW/scripts/sync_*.py`, `scripts/generate_*.py`, `scripts/check_major_event_trigger.py`
- Triggers: Cron jobs (08:00 pre-market), manual refresh, dashboard refresh API
- Responsibilities: Pull external data, compute derived context, write instance state files in strict sequential order

**Layered Review Cron:**
- Location: `skills/ETF_TW/scripts/layered_review_cron_registry_live.py`
- Triggers: Cron (daily, post-market)
- Responsibilities: T+1 / T+3 / T+10 review of past AI decisions; back-fills `ai_decision_outcome.jsonl` and `ai_decision_review.jsonl`

## Error Handling

**Strategy:** Defensive with hard gates and graceful degradation

**Patterns:**
- **Trading hours gate**: Hard exit (`sys.exit(1)`) when order attempted outside 09:00-13:30 / 13:40-14:30; function `is_trading_hours()` returns boolean for non-fatal checks
- **State I/O safety**: `safe_load_json()` returns default on any failure; `atomic_save_json()` uses temp file + rename to prevent corruption
- **AI Bridge fallback**: If AI is unavailable/stale, dashboard displays last valid response with stale badge; falls back to rule engine preview
- **Ghost order detection**: `broker_order_id: null` + `verified: false` + `order_id: ""` = phantom order; never reported as placed
- **Adapter import guards**: `try/except ImportError` around shioaji, yfinance, optional adapters (cathay, yuanlin)
- **DNS fix injection**: `dns_fix.py` patch applied at top of `run_auto_decision_scan.py` for sandbox environment compatibility
- **Provenance append-only**: Decision logs never deleted; `safe_append_jsonl()` uses `os.fsync()` for durability
- **Partial fill monotonicity**: `filled_quantity` can only advance, never retreat; enforced in `choose_preferred_row()`

## Cross-Cutting Concerns

**Logging:** `trade_logger.py` (`TradeLog` dataclass) writes to `data/trade_logs.jsonl`; dashboard log at `dashboard-5055.log`; provenance in `decision_provenance.jsonl`; separate Python `logging` module in sinopac adapter

**Validation:** `validate_order.py` (pre-trade checks), `risk_controller.py` (position/size/daily limits), `state_schema.py` (state file schema validation), `trading_hours_gate.py` (time-based gate)

**Authentication:** Broker credentials read from `instances/<agent_id>/private/.env` via `line.split('=', 1)` pattern; `instance_config.json` stores broker routing; shioaji authenticate via `api.login()` with person_id + password

**Multi-Tenancy:** `etf_core/context.py` routes all paths by `AGENT_ID` env var; each instance gets isolated `state/`, `logs/`, `private/`, `runtime/`, `temp/` directories; cross-instance state contamination prevented by defaulting to `etf_master` with warning

**Audit Trail:** Provenance logger (`decision_provenance.jsonl`), trade journal (`trade_journal/{date}.json`), fills ledger (`fills_ledger.json`), decision outcomes (`decision_outcomes.jsonl`), decision reviews (`decision_review.jsonl`, `ai_decision_review.jsonl`, `ai_decision_reflection.jsonl`)

**Timezone:** All timestamps use `Asia/Taipei` via `ZoneInfo('Asia/Taipei')`; trading hours comparison in local time

---

*Architecture analysis: 2026-04-15*