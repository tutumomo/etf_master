# Codebase Structure

**Analysis Date:** 2026-04-15

## Directory Layout

```
~/.hermes/profiles/etf_master/              # Hermes agent profile root
├── SOUL.md                                 # Agent persona (ETF_Master identity + rules)
├── config.yaml                             # Hermes runtime config (model, terminal, agent)
├── auth.json                               # Platform auth tokens (Telegram, etc.)
├── state.db                                # SQLite session store (Hermes conversations)
├── .env                                    # API keys (NEVER commit or read contents)
├── .skills_prompt_snapshot.json             # Cached skills prompt for agent
├── bin/                                    # Binary executables
├── cache/                                  # Runtime cache (documents, images, screenshots)
├── cron/                                   # Scheduled task definitions and output
│   ├── jobs.json                           # Cron job registry (health check, pre-market, etc.)
│   └── output/                            # Per-task execution output directories
├── logs/                                   # Hermes-level logs
├── memories/                               # Persistent agent memory files
├── plans/                                  # Planning artifacts
├── platforms/                              # Platform pairing configs
├── sandboxes/                              # Sandbox environments
├── scripts/                                # Profile-level utility scripts
├── sessions/                               # Conversation session data
├── skills/                                 # Installed skills (categorized)
│   ├── ETF_TW/                             # PRIMARY: Main trading skill
│   ├── stock-analysis-tw/                  # 8-dimension quantitative diagnostics
│   ├── stock-market-pro-tw/                # Professional charts (RSI/MACD/BB/VWAP)
│   ├── taiwan-finance/                     # DCF valuation, equity research, IB modeling
│   ├── etf-market-context-pipeline/       # Market context generation pipeline
│   ├── etf-tw/                            # ETF_TW iteration branches
│   ├── etf-tw-order-submit-monitor/       # Order submission monitoring
│   ├── opencli-explorer/                  # Browser automation
│   ├── opencli-oneshot/                   # One-shot CLI generation
│   ├── opencli-operate/                   # Browser operation
│   ├── opencli-usage/                     # Usage tracking
│   └── [~30 other skill categories]       # apple, creative, data-science, devops, etc.
├── skins/                                  # UI theme definitions
├── webui_state/                            # Web UI state
└── workspace/                              # Working directory
```

## ETF_TW Skill Structure (Primary Codebase)

```
skills/ETF_TW/
├── SKILL.md                                 # Skill manifest and documentation (47KB)
├── BOOT.md                                  # Boot sequence instructions
├── README.md                                # Quick reference
├── INSTALL.md                               # Setup instructions
├── .venv/                                   # Python virtual environment (MUST use for all execution)
├── .git/                                    # Separate git repo for ETF_TW
├── .learnings/                              # Agent learning artifacts
│   └── ERRORS.md                            # Error log
├── agent_template/                          # Template for new agent instances
│   ├── AGENTS.md                            # Boot rules
│   ├── IDENTITY.md                          # Agent identity template
│   └── SOUL.md                              # Agent persona template
├── assets/                                  # Static assets
├── data/                                    # Static/seed data (NOT instance state)
│   ├── broker_registry.json                 # Broker capability registry
│   ├── brokers.json                         # Broker connection configs
│   ├── etf_universe_tw.json                 # Full tradable ETF universe (TWSE + TPEx)
│   ├── etfs.json                            # Curated ETF metadata subset
│   ├── symbol_mappings.json                 # Symbol normalization mappings
│   ├── market_macro.json                    # Macro indicators seed
│   ├── paper_ledger.json                    # Paper trading ledger
│   ├── sample_orders.json                  # Sample order templates
│   └── trade_logs.jsonl                     # Trade execution log (append-only)
├── dashboard/                               # FastAPI web dashboard
│   ├── app.py                               # Main FastAPI application (48KB)
│   ├── README.md                            # Dashboard documentation
│   └── templates/
│       ├── base.html                        # Base Jinja2 template
│       └── overview.html                    # Main dashboard page template (65KB)
├── docs/                                    # Architecture and design documents
│   ├── STATE_ARCHITECTURE.md                # State truth source hierarchy
│   ├── AI_DECISION_BRIDGE.md                # AI bridge design and staged autonomy
│   ├── AI_DECISION_STATUS.md                # AI decision status tracking
│   ├── AI_AGENT_RESPONSE_LIFECYCLE.md       # Agent response lifecycle
│   ├── AI_RESEARCH_METHOD.md                # Research method quality fields
│   ├── BROKER_RECONCILIATION_RULES.md        # 4-layer precedence rules
│   ├── CRON_PACK_STANDARD.md                # Cron pack standard
│   ├── LAYERED_REVIEW_CRON_STANDARD.md      # Layered review cron standard
│   ├── LAYERED_REVIEW_SCHEDULING.md         # Review scheduling doc
│   ├── IMPROVEMENT_PLAN_V3.md               # v3 improvement roadmap
│   ├── SYMBOL_NORMALIZATION.md              # .TW/.TWO suffix convention
│   ├── shioaji_api_reference.md             # Shioaji API reference (25KB)
│   └── plugin-readiness-assessment.md       # Plugin system assessment
├── instances/                               # Multi-instance root
│   ├── etf_master/                          # Primary instance
│   │   ├── instance_config.json             # Instance-specific config (PRIVATE)
│   │   ├── strategy_state.json              # Strategy configuration (base + overlay)
│   │   ├── state/                           # SOLE TRUTH SOURCE (27+ files)
│   │   ├── logs/                            # Instance-specific logs
│   │   ├── private/                         # Certificates and secrets (NEVER commit)
│   │   │   └── certs/                       # Broker certificates
│   │   ├── wiki/                            # Knowledge files (market-view.md, risk-signal.md)
│   │   └── runtime/                         # PID files, locks
│   └── _deprecated_root_state/              # Legacy (DO NOT read for production)
├── private/                                 # Root-level private data
│   └── certs/                               # Broker certificate files
├── references/                              # Reference documents (SOPs, guides)
│   ├── risk-controls.md                     # Risk control reference
│   ├── live-trading-sop.md                  # Live trading SOP
│   ├── architecture_review_20260409.md      # Architecture review
│   ├── roadmap.md                           # Development roadmap
│   ├── trading-workflow.md                  # Trading workflow reference
│   ├── broker-onboarding.md                 # New broker onboarding guide
│   ├── beginner-guide.md                    # User guide
│   ├── api-integration.md                   # API integration reference
│   └── [15 more reference files]            # Phase docs, fix summaries, links
├── scripts/                                 # Core Python scripts (~100 files)
│   ├── etf_tw.py                            # CLI entry point (45KB)
│   ├── complete_trade.py                     # Order execution with risk + audit
│   ├── run_auto_decision_scan.py            # Dual decision consensus engine
│   ├── ai_decision_bridge.py                # AI bridge request/response builders
│   ├── risk_controller.py                   # Pre-trade risk checks
│   ├── trading_hours_gate.py                # Market hours enforcement
│   ├── venv_executor.py                     # Forces .venv python for execution
│   ├── provenance_logger.py                 # Append-only decision audit trail
│   ├── order_event_precedence.py            # 4-layer conflict resolution
│   ├── order_event_bridge.py                # Event normalization
│   ├── order_lifecycle.py                   # Status normalization + terminal detection
│   ├── fills_ledger.py                      # Fill facts record builder
│   ├── state_reconciliation_enhanced.py     # Order/position/fills reconciliation
│   ├── trade_journal.py                     # EOD journal + slippage analysis
│   ├── trade_logger.py                      # Trade execution logger
│   ├── poll_order_status.py                 # Order status polling with fills ledger sync
│   ├── account_manager.py                   # Multi-broker account routing
│   ├── broker_manager.py                    # Broker registration helper
│   ├── dashboard_guard.py                   # Dashboard health guardian
│   ├── dashboard_health.py                  # Health check payload builder
│   ├── market_calendar_tw.py                # Taiwan market calendar
│   ├── [20+ sync/generate scripts]          # Refresh pipeline (see Architecture)
│   ├── [10+ layered review scripts]         # T+1/T+3/T+10 decision review
│   ├── [5+ AI lifecycle scripts]            # AI quality, reflection, review, outcome
│   └── adapters/                            # Broker adapter implementations
│       ├── __init__.py                      # Package exports
│       ├── base.py                          # BaseAdapter ABC + data classes
│       ├── paper_adapter.py                 # Paper trading adapter
│       ├── sinopac_adapter.py              # SinoPac (Shioaji) live adapter
│       ├── sinopac_adapter_enhanced.py      # Enhanced SinoPac adapter
│       ├── cathay_adapter.py               # Cathay Securities adapter
│       └── yuanlin_adapter.py              # Yuanlin Securities adapter
├── scripts/etf_core/                        # Core utility library
│   ├── context.py                           # Instance context hub (get_state_dir, etc.)
│   ├── main_service.py                     # ETF_TW Pro legacy service class
│   ├── state_io.py                         # safe_load_json, atomic_save_json, safe_append_jsonl
│   ├── state_schema.py                     # State payload validation
│   ├── simulator.py                         # Paper trading simulator (SQLite-based)
│   ├── telegram_push.py                    # Telegram message formatting
│   ├── brokers/                             # Legacy broker interfaces
│   │   ├── base_broker.py                  # BaseBroker ABC (simpler, sync)
│   │   ├── broker_manager.py              # BrokerManager
│   │   ├── sinopac_broker.py              # SinoPac legacy broker
│   │   └── cathay_broker.py               # Cathay legacy broker
│   ├── db/
│   │   └── database.py                    # SQLite schema and operations
│   ├── utils/
│   │   ├── quote.py                       # yfinance quote fetching + technical indicators
│   │   └── news_crawler.py               # News RSS crawling
│   └── tests/
│       └── test_report_20260304.md         # Legacy test report
├── state/                                   # LEGACY root state (DO NOT use for new code)
├── tests/                                   # Pytest test suite (145 files, ~247 tests)
│   ├── test_ai_decision_bridge_*.py         # AI bridge contract tests
│   ├── test_auto_*.py                       # Auto-trade/quality/refresh tests
│   ├── test_broker_seq_precedence.py        # Broker sequence precedence tests
│   ├── test_callback_*.py                   # Callback normalization and consistency tests
│   ├── test_complete_trade_*.py             # Trade execution contract tests
│   ├── test_dashboard_*.py                  # Dashboard API/UI contract tests
│   ├── test_filled_reconciliation_*.py      # Reconciliation report tests
│   ├── test_fills_ledger_*.py               # Fill ledger I/O and merge tests
│   ├── test_generate_ai_*.py               # AI request/response generation tests
│   ├── test_instance_state_paths.py         # Instance path routing tests
│   ├── test_layered_review_*.py             # Review cron and scheduling tests
│   ├── test_live_state_contracts.py         # Live state sync contract tests
│   ├── test_market_*.py                     # Market calendar and intelligence tests
│   ├── test_order_*.py                      # Order event/lifecycle/precedence tests
│   ├── test_partial_fill_*.py               # Partial fill edge case tests
│   ├── test_poll_*.py                       # Polling contract tests
│   ├── test_sinopac_callback_*.py           # SinoPac callback tests
│   ├── test_state_reconciliation_*.py       # Reconciliation helper tests
│   ├── test_sync_*.py                       # Sync pipeline contract tests
│   ├── test_trading_mode.py                 # Trading mode state tests
│   ├── test_venv_executor.py               # Venv enforcement tests
│   └── test_verify_alignment_*.py           # Alignment verification tests
└── logs/                                    # Runtime logs (shioaji.log, etc.)
```

## Instance State Directory (Sole Truth Source)

```
instances/etf_master/state/
├── strategy_link.json                       # Strategy header (base_strategy + scenario_overlay)
├── positions.json                           # Current positions (TRUTH)
├── account_snapshot.json                    # Account balance snapshot (TRUTH)
├── orders_open.json                         # Active orders (TRUTH)
├── portfolio_snapshot.json                  # Portfolio aggregation (DERIVED)
├── watchlist.json                           # Monitored symbols
├── market_cache.json                        # Latest quote cache
├── market_intelligence.json                 # Technical indicators (RSI/MACD/SMA/BB)
├── market_context_taiwan.json               # Taiwan market regime/context
├── market_event_context.json                # Global event risk context
├── intraday_tape_context.json               # Intraday signal context
├── major_event_flag.json                    # Event trigger status
├── event_review_state.json                  # Event review tracking
├── agent_summary.json                       # Agent-consumable briefing (DISPLAY)
├── trading_mode.json                        # Paper/live mode state
├── auto_trade_config.json                   # Auto-trade settings
├── auto_trade_state.json                    # Auto-trade runtime state
├── auto_trade_submissions.json              # Submission history
├── auto_submit_state.json                   # Submission settings
├── auto_preview_candidate.json              # Current consensus candidate
├── context_weights.json                     # Decision context weights
├── decision_log.jsonl                        # Decision log (append-only)
├── decision_outcomes.jsonl                  # Decision outcomes (append-only)
├── decision_outcomes_dedup.jsonl            # Deduplicated outcomes
├── decision_provenance.jsonl                # Full provenance trail (append-only)
├── decision_review.jsonl                    # Decision reviews (append-only)
├── decision_quality.json                    # Quality scoring
├── decision_experiments.json                 # A/B experiment config
├── decision_reasoning.json                  # LLM reasoning cache
├── decision_context_history.jsonl           # Decision context snapshots
├── decision_outcome_summary.json            # Outcome statistics
├── ai_decision_request.json                 # AI bridge request artifact
├── ai_decision_response.json                # AI bridge response artifact
├── ai_decision_quality.json                 # AI decision quality state
├── ai_decision_outcome.jsonl               # AI decision outcomes (append-only)
├── ai_decision_review.jsonl                 # AI decision reviews (append-only)
├── ai_decision_reflection.jsonl            # AI decision reflections (append-only)
├── macro_indicators.json                    # Macro economic indicators
├── central_bank_calendar.json               # Central bank meeting calendar
├── market_view.md                           # Market regime wiki
├── risk_signal.md                           # Risk signal wiki
├── news_headlines.json                      # Recent headlines
├── news_articles.json                       # Article contents
├── regime_bucket_stats.json                 # Regime distribution statistics
├── filled_reconciliation.json               # Fill reconciliation report
├── layered_review_*.json/jsonl              # Review scheduling and registrations
├── family_identity.json                     # Agent family identity
├── trade_journal/                           # EOD journal archives
│   ├── 2026-03-30.json ... 2026-04-13.json  # Daily journal files
└── layered_review_reviews/                  # Review artifact storage
```

## Directory Purposes

**skills/ETF_TW/scripts/:**
- Purpose: All Python business logic -- trading, sync, decision, review
- Contains: ~100 Python files organized by concern (not by traditional MVC)
- Key files: `etf_tw.py` (CLI entry), `run_auto_decision_scan.py` (consensus engine), `complete_trade.py` (order execution)

**skills/ETF_TW/scripts/adapters/:**
- Purpose: Broker abstraction layer (Strategy pattern)
- Contains: 6 files; `base.py` defines ABC + data classes + factory; concrete adapters implement broker-specific logic
- Key files: `base.py` (BaseAdapter), `sinopac_adapter.py` (production adapter)

**skills/ETF_TW/scripts/etf_core/:**
- Purpose: Shared infrastructure -- context routing, state I/O, schema validation, legacy service, simulator
- Contains: Core utility modules used by every other script
- Key files: `context.py` (instance routing), `state_io.py` (atomic persistence)

**skills/ETF_TW/instances/etf_master/state/:**
- Purpose: SOLE TRUTH SOURCE for all runtime data
- Contains: 27+ JSON/JSONL files; truth files (positions, orders, account), derived files (summaries, intelligence), audit trails (JSONL logs)
- Key files: `positions.json`, `orders_open.json`, `account_snapshot.json` (truth); `agent_summary.json` (display)

**skills/ETF_TW/dashboard/:**
- Purpose: Web UI and API for monitoring and control
- Contains: FastAPI application and Jinja2 templates
- Key files: `app.py` (48KB monolithic FastAPI app)

**skills/ETF_TW/tests/:**
- Purpose: Contract and integration tests for all scripts
- Contains: 145 test files following `test_<feature>_<aspect>.py` naming
- Key files: Tests are co-located in single flat directory (not mirroring source structure)

**skills/ETF_TW/data/:**
- Purpose: Static/seed data; NOT runtime state
- Contains: Broker registry, ETF universe, symbol mappings, trade log file
- Key files: `broker_registry.json`, `etf_universe_tw.json`, `trade_logs.jsonl`

**skills/ETF_TW/docs/:**
- Purpose: Architecture and design documents (truth rules, reconciliation, AI bridge)
- Contains: 13 markdown documents
- Key files: `STATE_ARCHITECTURE.md`, `AI_DECISION_BRIDGE.md`, `BROKER_RECONCILIATION_RULES.md`

**skills/ETF_TW/references/:**
- Purpose: Operational references (SOPs, onboarding, troubleshooting)
- Contains: 21 reference documents
- Key files: `risk-controls.md`, `live-trading-sop.md`, `roadmap.md`

## Key File Locations

**Entry Points:**
- `skills/ETF_TW/scripts/etf_tw.py`: CLI entry point (argparse-based, 45KB)
- `skills/ETF_TW/dashboard/app.py`: FastAPI web server entry point (48KB)
- `skills/ETF_TW/scripts/venv_executor.py`: Safe script execution wrapper
- `skills/ETF_TW/scripts/run_auto_decision_scan.py`: Decision engine entry point

**Configuration:**
- `config.yaml`: Hermes agent runtime configuration
- `SOUL.md`: Agent persona and behavioral rules
- `skills/ETF_TW/instances/etf_master/instance_config.json`: Instance-specific config
- `skills/ETF_TW/instances/etf_master/strategy_state.json`: Strategy base + overlay
- `skills/ETF_TW/data/broker_registry.json`: Broker capability definitions
- `skills/ETF_TW/data/brokers.json`: Broker connection configs

**Core Logic:**
- `skills/ETF_TW/scripts/adapters/base.py`: Broker adapter ABC + factory
- `skills/ETF_TW/scripts/etf_core/context.py`: Instance routing hub
- `skills/ETF_TW/scripts/etf_core/state_io.py`: Atomic JSON persistence
- `skills/ETF_TW/scripts/order_event_precedence.py`: 4-layer conflict resolution
- `skills/ETF_TW/scripts/risk_controller.py`: Pre-trade risk validation
- `skills/ETF_TW/scripts/trading_hours_gate.py`: Market hours hard gate

**State (Instance Truth):**
- `skills/ETF_TW/instances/etf_master/state/positions.json`: Position truth
- `skills/ETF_TW/instances/etf_master/state/orders_open.json`: Order truth
- `skills/ETF_TW/instances/etf_master/state/account_snapshot.json`: Account truth
- `skills/ETF_TW/instances/etf_master/state/ai_decision_request.json`: AI bridge request
- `skills/ETF_TW/instances/etf_master/state/ai_decision_response.json`: AI bridge response

**Testing:**
- `skills/ETF_TW/tests/`: 145 test files (flat directory)
- Run with: `.venv/bin/python3 -m pytest tests/ -q`

## Naming Conventions

**Files:**
- Python scripts: `snake_case.py` (e.g., `sync_market_cache.py`, `generate_intraday_tape_context.py`)
- Test files: `test_<feature>_<aspect>.py` (e.g., `test_poll_order_status_contract.py`, `test_callback_terminal_statuses.py`)
- State files: `snake_case.json` for single objects; `snake_case.jsonl` for append-only logs
- Sync scripts: `sync_<what>.py` (e.g., `sync_strategy_link.py`, `sync_market_cache.py`)
- Generate scripts: `generate_<what>.py` (e.g., `generate_market_event_context.py`)
- Documentation: `UPPER_SNAKE_CASE.md` (e.g., `STATE_ARCHITECTURE.md`, `AI_DECISION_BRIDGE.md`)
- References: `kebab-case.md` (e.g., `risk-controls.md`, `live-trading-sop.md`)

**Directories:**
- Skill directories: `SCREAMING_SNAKE_CASE` for primary (e.g., `ETF_TW/`), `kebab-case` for others (e.g., `stock-analysis-tw/`)
- Instance directories: Match `AGENT_ID` value (e.g., `etf_master/`)
- Adapter files: Lowercase with `_adapter.py` suffix (e.g., `sinopac_adapter.py`)

**Python Modules:**
- Package init: `__init__.py` with explicit `__all__` exports
- Core library: `etf_core/` package under `scripts/`
- Functions: `snake_case` (e.g., `get_state_dir()`, `build_strategy_payload()`)
- Classes: `PascalCase` (e.g., `BaseAdapter`, `AccountManager`, `RiskController`)
- Dataclasses: `PascalCase` (e.g., `Order`, `Position`, `AccountBalance`, `RiskCheckResult`)

## Where to Add New Code

**New Broker Adapter:**
1. Create `skills/ETF_TW/scripts/adapters/<broker>_adapter.py` -- subclass `BaseAdapter`, implement 7 abstract methods
2. Import in `skills/ETF_TW/scripts/adapters/__init__.py` -- add to `__all__`
3. Register in `skills/ETF_TW/scripts/adapters/base.py` `get_adapter()` -- add to `adapter_map`
4. Register in `skills/ETF_TW/data/broker_registry.json` -- add broker entry with capabilities and credentials
5. Update `skills/ETF_TW/scripts/account_manager.py` -- add adapter instantiation
6. Add test: `skills/ETF_TW/tests/test_<broker>_adapter_contract.py`

**New Sync Script:**
1. Create `skills/ETF_TW/scripts/sync_<what>.py` or `generate_<what>.py`
2. Follow refresh pipeline pattern: import `context`, set `STATE_DIR = context.get_state_dir()`, use `atomic_save_json()` for output
3. Insert into pipeline ORDER (update `docs/STATE_ARCHITECTURE.md`)
4. Add to cron job prompt if needed (update `cron/jobs.json`)
5. Add test: `skills/ETF_TW/tests/test_sync_<what>.py`

**New Dashboard Page/Endpoint:**
1. Add API endpoint in `skills/ETF_TW/dashboard/app.py` (FastAPI router)
2. Add template in `skills/ETF_TW/dashboard/templates/<page>.html`
3. Read from instance state ONLY via `context.get_state_dir()`
4. Add test: `skills/ETF_TW/tests/test_dashboard_<feature>.py`

**New State File:**
1. Create file via `atomic_save_json()` in the appropriate sync script
2. Place in `instances/<agent_id>/state/<name>.json` (single object) or `.jsonl` (append-only log)
3. Document in `docs/STATE_ARCHITECTURE.md`
4. Add schema validation in `scripts/etf_core/state_schema.py` (`REQUIRED_KEYS` dict)
5. Add test: `skills/ETF_TW/tests/test_<name>_contract.py`

**New Test:**
1. Create `skills/ETF_TW/tests/test_<feature>_<aspect>.py`
2. Use `.venv/bin/python3 -m pytest` to run
3. Import scripts via `sys.path.insert(0, ...)` pointing to `scripts/` directory
4. Use `_isolate_hermes_home` autouse fixture from `tests/conftest.py` -- test state writes go to temp dir
5. Never write to `~/.hermes/` in tests

**New Decision Pipeline Component:**
1. Create script in `skills/ETF_TW/scripts/`
2. Read state from instance dir, write decision artifacts following bridge contract
3. Update `run_auto_decision_scan.py` to invoke new component
4. Add provenance logging via `provenance_logger.py`
5. Add T+1/T+3/T+10 review integration in `layered_review_cron_registry_live.py`

## Special Directories

**skills/ETF_TW/instances/etf_master/private/:**
- Purpose: Broker certificates, API keys, secrets
- Generated: Partially (certs from broker), partially manual (instance_config.json)
- Committed: No -- must NEVER be committed to git

**skills/ETF_TW/instances/etf_master/state/:**
- Purpose: Sole truth source for all runtime data (27+ files)
- Generated: Yes -- built entirely by sync/generate scripts
- Committed: No -- runtime data only; `.gitkeep` at root for directory preservation

**skills/ETF_TW/.venv/:**
- Purpose: Isolated Python environment with shioaji, yfinance, fastapi, etc.
- Generated: Yes -- via `python -m venv .venv && source .venv/bin/activate && pip install -r ...`
- Committed: No -- MUST use `.venv/bin/python3` for all script execution

**skills/ETF_TW/state/ (LEGACY):**
- Purpose: Deprecated root-level state directory
- Generated: Historical artifact
- Committed: No
- IMPORTANT: DO NOT read from this directory for production logic; always use instance state

**cron/output/:**
- Purpose: Captured output from scheduled cron task executions
- Generated: Yes -- by Hermes cron system
- Committed: No

**cache/:**
- Purpose: Hermes-level runtime cache (documents, images, screenshots)
- Generated: Yes -- by Hermes agent tools
- Committed: No

**memories/:**
- Purpose: Persistent memory files consumed by the agent
- Generated: Yes -- by Hermes memory system
- Committed: Yes (some memory files contain reusable knowledge)

---

*Structure analysis: 2026-04-15*