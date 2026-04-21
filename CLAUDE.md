# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **etf_master** Hermes agent profile — a Taiwan ETF investment assistant with a 5-skill financial ecosystem. The profile lives at `~/.hermes/profiles/etf_master/` and is a Hermes Agent installation (by Nous Research).

## Agent Identity (SOUL.md)

ETF_Master is a "risk-first" financial assistant. Core rules from SOUL.md that affect all code in this repo:

- **Risk > Return**: Never promise returns. Any high-return narrative must accompany risk explanation.
- **Don't screw up big**: If data is insufficient, signals conflict, or costs are unclear — default to inaction.
- **Execution/Advice Separation**: Analysis, comparison, verification are fine; real-money execution requires explicit authorization.
- **7 Bell Disciplines**: Single-turn completion, no A/B on explicit commands, pre-flight all checks at once, verify API response != order landed, query orders+positions together, response length inversely proportional to user frustration, venv enforcement on live submits.
- **Strategy Header**: Every reply must prefix with `[目前投資策略:XXX, 情境覆蓋:YYY]` from `strategy_link.json`.

## Financial Ecosystem (5 Skills)

| Skill | Role | Has Tests? |
|-------|------|-----------|
| **ETF_TW** | Order management, monitoring, state truth, Shioaji API | Yes (164 files, 364 tests) |
| **stock-analysis-tw** | 8-dimension quantitative diagnostics | No |
| **stock-market-pro-tw** | Professional charts (RSI/MACD/BB/VWAP/ATR) | No |
| **taiwan-finance** | DCF valuation, equity research, IB modeling, PE, wealth management | No |
| **opencli-explorer/oneshot/operate/usage** | Browser automation & CLI generation | No |

Data flow per SOUL.md alignment principle: **analysis** from stock-analysis + taiwan-finance → **verification** from stock-market-pro → **execution** by ETF_TW → **learning** via Self-Evolution.

## ETF_TW Architecture (Critical)

### State Architecture — Single Source of Truth

**Instance state is the sole truth source**: `skills/ETF_TW/instances/<agent_id>/state/`

- Root `ETF_TW/state/` is legacy — do NOT read from it for production logic.
- Dashboard and sync scripts must both read/write instance state.
- **Downstream summaries must NEVER overwrite upstream truth**: `agent_summary.json`, `intraday_tape_context.json` are display layer; they cannot overwrite `positions.json`, `account_snapshot.json`, `orders_open.json`.

### Refresh Pipeline (11 scripts, sequential order matters)

1. `sync_strategy_link.py` → 2. `sync_live_state.py` / `sync_paper_state.py` → 3. `sync_market_cache.py` → 4. `generate_market_event_context.py` → 5. `generate_taiwan_market_context.py` → 6. `check_major_event_trigger.py` → 7. `sync_portfolio_snapshot.py` → 8. `sync_ohlcv_history.py` → 9. `generate_intraday_tape_context.py` → 10. `sync_agent_summary.py` → 11. `sync_worldmonitor.py --mode daily`

> **Intraday watch (independent cron)**: `sync_worldmonitor.py --mode watch` every 30 min during market hours — detects L2/L3 risk escalations and appends to `worldmonitor_alerts.jsonl`.

> **Post-market review (independent cron, 15:05 weekday)**: `sync_decision_reviews.py` — scans provenance for T1/T3/T10 windows due, backfills prices and verdicts, finalizes `outcome_final`, updates `decision_quality_report.json` chain_breakdown.

> **Weekly report (independent cron, 09:05 Saturday)**: `generate_decision_quality_weekly.py` — writes `wiki/decision-weekly-YYYY-WNN.md` and `wiki/decision-quality-latest.md`.

### AI Decision Bridge

The bridge is at `scripts/ai_decision_bridge.py`. It follows a staged autonomy model:
- **Stage 0**: Rule-based preview (current)
- **Stage 1**: AI writes `ai_decision_request.json` → reads → writes `ai_decision_response.json` (no auto-trade)
- **Stage 2**: Request/Response/Outcome/Reflection retention + quality review
- **Stage 3**: Controlled autonomy (AI creates previews, adds risk tags — still no live submit)

Key contract files in instance state: `ai_decision_request.json`, `ai_decision_response.json`, `ai_decision_outcome.jsonl`, `ai_decision_review.jsonl`

**`ai_decision_request.json` now aggregates 15 input sources** (as of v1.4.4/v1.4.5):
- Sources 1–13: market cache, positions, strategy link, OHLCV, event context, Taiwan market context, intraday tape, portfolio snapshot, open orders, agent summary, quality report, event review state, daily order limits
- Source 14: `worldmonitor_context` — global risk signals (supply chain / geopolitical / taiwan strait)
- Source 15: `wiki_context` — 4 fields: `market_view`, `risk_signal`, `investment_strategies`, `undervalued_ranking`

**Wiki path resolution** in `generate_ai_decision_request.py`: auto-discovers profile wiki at `~/.hermes/profiles/<profile>/wiki/` then falls back to instance wiki. Supports both `{SYMBOL}.md` and slug form (e.g. `0050-yuanta-taiwan-50.md`) for entity pages.

### Dual Decision Consensus

Two parallel decision pipelines converge via `resolve_consensus()` in `run_auto_decision_scan.py`:
- **Rule engine** (deterministic, auditable) — has veto power
- **AI Decision Bridge** (`ai_decision_bridge.py`) — LLM-augmented reasoning

Consensus tiers: **Tier 1** (both agree → high confidence) → **Tier 2** (disagreement → rule engine wins, lower confidence) → **Tier 3** (opposite → locked, requires human).

### Broker Reconciliation: 4-Layer Precedence

When submit_response, submit_verification, broker_polling, and broker_callback all update the same order:
1. **Status rank**: terminal states (filled/cancelled/rejected) cannot be overwritten
2. **Timestamp precedence**: `event_time` > `observed_at`
3. **broker_seq precedence**: higher wins
4. **Source priority**: callback(4) > polling(3) > submit_verification(2) > submit_response(1) > local_inference(0)

Partial fills are monotonic: `filled_quantity` can only advance, never retreat.

### Broker Adapter Pattern

`scripts/adapters/base.py` (BaseAdapter) → `paper_adapter.py`, `sinopac_adapter.py`, `sinopac_adapter_enhanced.py`, `cathay_adapter.py`, `yuanlin_adapter.py`

New brokers: subclass BaseAdapter, register in `data/broker_registry.json`, add entry in `AccountManager`.

### Multi-Instance (Context)

`scripts/etf_core/context.py` is the configuration hub — `get_instance_config()`, `get_broker_config()`, `get_instance_dir()` etc. All instance-specific paths route through here. It connects Broker Registry, Account & Auth, and Market Cache communities.

## Hard Constraints (Must Never Violate)

### Trading Hours Gate
- **General session**: 09:00–13:30
- **After-hours odd lot**: 13:40–14:30
- **Outside these hours**: reply "現在非交易時段，無法下單" — no attempt to submit.

### Risk Controls (Three-No Principles)
1. **No profit promises**: never guarantee annualized returns
2. **No auto live trading**: default is paper mode; live requires explicit authorization
3. **No skipping risk checks**: validate → preview → confirm → execute

### Concentration Limits
- Single ETF ≤ 60% (configurable)
- Single trade ≤ 50% of portfolio (unless user says "CONFIRM LARGE ORDER")
- Unit confusion (張 vs 股): if 10x beyond average position — **must pause and confirm**

### venv Enforcement
All live order submissions must use: `skills/ETF_TW/.venv/bin/python`

## Common Commands

```bash
# Dashboard
cd ~/.hermes/profiles/etf_master/skills/ETF_TW && .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055

# Run ETF_TW tests (must use venv python)
cd ~/.hermes/profiles/etf_master/skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q                                    # Full suite
.venv/bin/python3 -m pytest tests/test_ai_decision_bridge_contract.py -q  # Single file
.venv/bin/python3 -m pytest tests/ -q -k "test_poll_order_status"         # By test name

# CLI entry point
.venv/bin/python3 scripts/etf_tw.py welcome     # Agent greeting
.venv/bin/python3 scripts/etf_tw.py portfolio   # Portfolio report
.venv/bin/python3 scripts/etf_tw.py check --install-deps  # Dependency check

# Multi-instance (e.g. etf_master + etf_master_wife in parallel)
AGENT_ID=etf_master      DASHBOARD_PORT=5055 .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055
AGENT_ID=etf_master_wife DASHBOARD_PORT=5056 .venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5056

# Verify a specific instance
AGENT_ID=etf_master      DASHBOARD_PORT=5055 bash scripts/verify_deployment.sh
AGENT_ID=etf_master_wife DASHBOARD_PORT=5056 bash scripts/verify_deployment.sh
```

## Key File Locations

| What | Path |
|------|------|
| Agent persona | `SOUL.md` |
| Boot sequence | `skills/ETF_TW/BOOT.md` |
| Agent template identity | `skills/ETF_TW/agent_template/IDENTITY.md` |
| Agent template SOUL | `skills/ETF_TW/agent_template/SOUL.md` |
| Agent template boot rules | `skills/ETF_TW/agent_template/AGENTS.md` |
| Risk controls reference | `skills/ETF_TW/references/risk-controls.md` |
| Live trading SOP | `skills/ETF_TW/references/live-trading-sop.md` |
| Shioaji API reference | `skills/ETF_TW/docs/shioaji_api_reference.md` |
| State architecture doc | `skills/ETF_TW/docs/STATE_ARCHITECTURE.md` |
| AI Decision Bridge doc | `skills/ETF_TW/docs/AI_DECISION_BRIDGE.md` |
| Broker reconciliation rules | `skills/ETF_TW/docs/BROKER_RECONCILIATION_RULES.md` |
| Symbol normalization | `skills/ETF_TW/docs/SYMBOL_NORMALIZATION.md` |
| Instance state (truth) | `skills/ETF_TW/instances/<agent_id>/state/` |
| Private config (NEVER commit) | `skills/ETF_TW/instances/<agent_id>/instance_config.json` |
| Version changelog | `skills/ETF_TW/CHANGELOG.md` |
| Wiki knowledge base (profile) | `wiki/` — **主寫層**，直接編輯這裡 |
| Wiki knowledge base (skill) | `skills/ETF_TW/wiki/` — 4 個標準頁是 symlink，指向 profile wiki；`entities/` 為 skill-only |
| Decision auto-review cron | `skills/ETF_TW/scripts/sync_decision_reviews.py` (15:05 weekday) |
| Decision weekly report cron | `skills/ETF_TW/scripts/generate_decision_quality_weekly.py` (09:05 Saturday) |
| Decision weekly wiki | `wiki/decision-weekly-YYYY-WNN.md` + `wiki/decision-quality-latest.md` |
| Deployment health check | `scripts/verify_deployment.sh` |

## Naming Conventions

- **Test files**: `test_<feature>_<aspect>.py` — e.g. `test_poll_order_status_contract.py`
- **Sync scripts**: `sync_<what>.py` — always write to instance state
- **State files**: lowercase snake_case `.json` or `.jsonl` (append-only for logs)
- **Symbols**: Canonical form without `.TW`/`.TWO` suffix internally; add provider-layer suffix only for external API calls (see SYMBOL_NORMALIZATION.md)

## Shioaji API Pitfalls (from production incidents)

- `api.stock_account` is a **property**, not a method — do not call it with `()`
- `api.logout()` **segfaults** — never call it; let the process exit naturally
- Broker order ID is in `trade.order.ordno`, NOT `trade.status.order_id`
- `ETF_PATH` vs `ETF_CURATED_PATH` — these are different variables; mixing them up silently broke 3 commands

## Cron/Sandbox Path Mismatch

In `execute_code`, `os.path.expanduser("~")` resolves correctly. But in `terminal()` shell context, `~` and `$HOME` point to sandbox `/root/`, not the real home. Also, `read_file()` returns line-numbered format that breaks `json.loads()` — JSON state files must be read via Python `open()` or shell piping.

## Ticker Suffix Convention

- yfinance: most Taiwan ETFs use `.TW`; TPBS-listed ETFs use `.TWO` (e.g. 00679B → 00679B.TWO). Rule: prefix 006 → `.TWO`, others → `.TW`
- Shioaji: TSE ETFs use `api.Contracts.Stocks.TSE.TSE0050`, OTC ETFs use `api.Contracts.Stocks.OTC.get('00679B')`

## Important Rules for Code Changes

1. **Never delete or overwrite instance state files** — sync scripts append/update, they don't replace wholesale.
2. **New adapter**: subclass `BaseAdapter`, implement required methods, register in `broker_registry.json`, update `AccountManager`.
3. **New sync script**: must follow the refresh pipeline order; write to instance state, not root state.
4. **New test**: use `.venv/bin/python3 -m pytest`; import scripts via `sys.path.insert(0, ...)` pointing to `scripts/`.
5. **Instance config is private** — `.env`, certificates, `instance_config.json` must never be committed.
6. **Dashboard reads instance state** — any new dashboard page must read from `instances/<agent_id>/state/`, not from legacy paths.
7. **Shioaji live orders**: must go through venv python, must validate trading hours, must verify via `list_trades()` after submission.
8. **Ghost order detection**: `broker_order_id: null` + `verified: false` + `order_id: ""` = phantom order — NEVER report as placed.
9. **Credential reading**: `read_file()` masks API keys as `***`; must use Python `open()` + `line.split('=', 1)` to read `private/.env`.
10. **Cron output**: all cron task output must be in Traditional Chinese.
11. **worldmonitor API schema**: `chokepoints[].disruptionScore/status/warRiskTier` — NO `global_stress_level` field; derive it via `_derive_global_stress_level()`. Shipping stress fields are `stressScore`/`stressLevel`, not `shipping_stress_index`.
12. **worldmonitor bot filter**: `middleware.ts` blocks `python-requests`/`curl` UA before auth. Always send `User-Agent: Mozilla/5.0 ETF-Master/1.0` header.
13. **worldmonitor config**: lives in `instance_config.json` under `"worldmonitor": {"enabled": bool, "base_url": "...", "api_key": "..."}`. Template at `instance_config.json.example`. Set `enabled: false` if no API key.
14. **`worldmonitor_alerts.jsonl` is append-only** — never overwrite; L3 alerts auto-trigger `check_major_event_trigger.py`.
15. **Wiki knowledge base** (`skills/ETF_TW/wiki/` and profile-level `wiki/`): 4 standard pages injected into AI Decision Request — `market-view.md`, `risk-signal.md`, `investment-strategies.md`, `undervalued-etf-ranking.md`. Add new wiki pages here; they are auto-discovered by path prefix matching.
16. **`sync_live_state.py` market_value fix**: Shioaji API may return `market_value=0` on positions; script now recalculates from `quantity × close_price` when this happens. `total_equity` is always recomputed as `cash + market_value`.
17. **Multi-instance deployment**: New instances created via `hermes profile create <name> --clone-from etf_master`. Instance state lives under `skills/ETF_TW/instances/<name>/state/`. Use `AGENT_ID=<name> DASHBOARD_PORT=<port>` to run in parallel. Verify with `bash scripts/verify_deployment.sh`.
18. **`verify_deployment.sh`**: Run from profile root with `AGENT_ID=<id> DASHBOARD_PORT=<port> bash scripts/verify_deployment.sh`. Positions check reads `/api/overview.positions` (not `/api/positions` which does not exist). Trading hours gate uses `validate-order` subcommand.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**ETF_TW / Hermes 遷移後穩定化與交易流程保險絲收斂計劃**

ETF_TW 是一個建構在 Hermes Agent 上的台灣 ETF 投資助理，核心功能包含持倉管理、自動決策掃描、Shioaji 券商下單、dashboard 監控。經歷 kimi-2.7 錯誤下單事件後，需要把已有的修復成果正式化，並補齊交易保險絲、真相層級治理、持倉交易票據等功能，產出可驗證、可回滾、可追蹤的變更紀錄。

**Core Value:** **交易安全優先於功能完備** — 任何時候，保險絲能擋住錯誤指令，比新增功能更重要。

### Constraints

- **Tech:** Python 3.14+ / Shioaji SDK / FastAPI dashboard / Hermes Agent framework
- **Timeline:** 優先完成保險絲收斂，再處理 UI
- **Trading hours:** 09:00-13:30（一般）、13:40-14:30（盤後零股）
- **硬限制：**
  1. 禁止混用 OpenClaw 舊路徑與 Hermes active 路徑
  2. 禁止把 state/dashboard 當成 live 事實
  3. 禁止「submit 回傳成功」就宣告委託已落地
  4. 禁止用過時單位口號（非 1000 倍數一定拒絕）
  5. 所有正式送單路徑必須走 pre-flight gate
  6. 每個階段必須 commit，最終必須 push
  7. 只改 active 副本，不改歷史輸出當現行規則
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14.3 — All skill implementations, automation scripts, dashboard, broker adapters, test suite
- YAML — Configuration (`config.yaml`), skill manifests (`SKILL.md` frontmatter), skin themes
- JSON — State files, broker registry, ETF universe, trade logs, instance configuration
- HTML/Jinja2 — Dashboard templates (`dashboard/templates/base.html`, `dashboard/templates/overview.html`)
- Markdown — Reference docs, SOUL.md, AGENTS.md, wiki pages
- Shell — Dashboard startup script (`scripts/start_dashboard.sh`)
- SQL (SQLite dialect) — Session database (`state.db`), legacy ETF_TW database (`etf_core/db/etf_tw.db`)
## Runtime
- Python 3.14.3 — Dedicated venv at `skills/ETF_TW/.venv/`
- Hermes Agent v0.9.0 — Core agent framework (installed at `~/.hermes/hermes-agent/`)
- pip (via venv) — ETF_TW and all skill dependencies
- uv — Stock-analysis-tw and stock-market-pro-tw scripts use `uv run --script` inline dependency declarations
- Lockfile: Not present (no poetry.lock or requirements.lock)
## Frameworks
- FastAPI 0.135.2 — Dashboard REST API (20 endpoints) at `skills/ETF_TW/dashboard/app.py`
- Uvicorn 0.42.0 — ASGI server for dashboard (port 5055)
- Pydantic 2.12.3 — Request/response models for dashboard API, config validation
- Starlette 1.0.0 — Underlying FastAPI web framework
- pytest 9.0.2 — Test runner; 145 test files in `skills/ETF_TW/tests/`
- Hermes Agent CLI (`hermes`) — Agent management, model switching, gateway, config
- Jinja2 3.1.6 — Template rendering for dashboard HTML
## Key Dependencies
- shioaji 1.3.2 — SinoPac Securities (永豐金證券) Python SDK for live trading
- yfinance 1.2.0 — Yahoo Finance market data (quotes, OHLCV, fundamentals)
- pandas 3.0.1 — Data manipulation for price analysis, OHLCV processing
- numpy 2.4.3 — Numerical computations, technical indicator calculations
- peewee 4.0.2 — ORM for legacy database operations in `etf_core/db/`
- httpx 0.28.1 — Async HTTP client (Hermes core)
- requests 2.32.5 — Synchronous HTTP for RSS feeds, LLM API calls, news crawling
- beautifulsoup4 4.14.3 — HTML parsing for web scraping
- feedparser 6.0.12 — RSS/Atom feed parsing for news collection
- loguru 0.7.3 — Structured logging
- rich 14.3.3 — Terminal formatting and tables
- orjson 3.11.7 — Fast JSON serialization
- sentry-sdk 2.55.0 — Error tracking (installed in venv, integration usage TBD)
- matplotlib — Stock chart rendering (stock-market-pro-tw)
- mplfinance — Candlestick/financial chart plotting (stock-market-pro-tw)
- plotille — Terminal ASCII charts (stock-market-pro-tw)
## Configuration
- Hermes profile config: `config.yaml` — model, display, tools, memory, terminal, privacy
- Agent persona: `SOUL.md` — risk-first investment assistant rules
- Instance config: `skills/ETF_TW/instances/etf_master/instance_config.json` — broker accounts, credentials (private)
- Environment vars: `.env` file present at profile root — contains API keys and secrets (NEVER read contents)
- Shell env vars for instance identity: `AGENT_ID`, `OPENCLAW_AGENT_NAME`
- ETF_TW venv: `skills/ETF_TW/.venv/` — isolated Python with all trading dependencies
- Dashboard: `uvicorn dashboard.app:app --host 0.0.0.0 --port 5055`
- Skills use `uv run --script` with inline PEP 723 dependency declarations
## Platform Requirements
- macOS (Darwin 25.0.0) — Current development platform
- Python 3.14+ required for ETF_TW venv
- Hermes Agent v0.9.0 installed system-wide
- Internet access for yfinance, RSS feeds, LLM APIs
- Hermes Agent runtime (local or containerized)
- SinoPac Securities account for live trading (optional)
- Dashboard served via uvicorn on port 5055
- Cron scheduler for market scanning (weekday schedules)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Code Style
### Python
- **Version:** Python 3.14+ required
- **Imports:** Standard library → third-party → local, grouped with blank lines
- **String formatting:** f-strings preferred over `.format()` or `%`
- **Type hints:** Sparse — used in Pydantic models and dashboard API schemas, mostly absent in scripts
- **Docstrings:** Minimal — most functions rely on clear naming and inline comments
- **Line length:** No explicit limit enforced (no black/ruff config found)
- **Chinese comments:** Common in trading logic — `# 檢查交易時段`, `# 建議先觀望`
### Module Loading Pattern
### YAML Configuration
- Hermes config: `config.yaml` — uses dot-notation keys (`display.skin`, `tools.enabled`)
- Skill manifests: `SKILL.md` with YAML frontmatter
## Naming Conventions
### Files
- **Test files:** `test_<feature>_<aspect>.py` — e.g., `test_poll_order_status_contract.py`
- **Sync scripts:** `sync_<what>.py` — always write to instance state
- **State files:** lowercase snake_case `.json` or `.jsonl` (append-only for logs)
- **Adapter files:** `<broker>_adapter.py` (e.g., `sinopac_adapter.py`)
### Symbols/Tickers
- **Internal:** Canonical form without `.TW`/`.TWO` suffix (e.g., `0050`, `00679B`)
- **yfinance:** Most Taiwan ETFs use `.TW`; TPBS-listed (prefix 006) use `.TWO`
- **Shioaji:** TSE ETFs via `api.Contracts.Stocks.TSE.TSE0050`; OTC via `api.Contracts.Stocks.OTC.get('00679B')`
- **Rule:** Prefix `006` → `.TWO`, others → `.TW` (for yfinance)
### Functions
- **Snake_case** for all function names
- **Private:** Leading underscore `_helper_function()`
- **Boolean returns:** Prefixed with `is_`, `has_`, `can_`
- **JSON handlers:** `build_*`, `sync_*`, `generate_*` patterns
## Error Handling
### Trading Scripts
- **Explicit validation** before order submission: trading hours, concentration limits, quantity checks
- **Never auto-trade live** without explicit authorization — default is paper mode
- **Three-No Principles:** No profit promises, no auto live trading, no skipping risk checks
- **Ghost order detection:** `broker_order_id: null` + `verified: false` + `order_id: ""` = phantom — never report as placed
### Broker Reconciliation (4-Layer Precedence)
- Partial fills: `filled_quantity` can only advance, never retreat
### API Error Handling
- Shioaji errors caught and logged via `loguru`
- yfinance rate limiting: retry with backoff (no formal retry library)
- Dashboard: FastAPI exception handlers return structured JSON errors
## Configuration Patterns
### Instance-based Configuration
- **Instance config:** `skills/ETF_TW/instances/<agent_id>/instance_config.json` — private, NEVER committed
- **Broker registry:** `skills/ETF_TW/data/broker_registry.json` — maps adapter names to classes
- **Strategy link:** `strategy_link.json` — determines strategy header for all replies
### Environment Variables
- `.env` file at profile root — API keys and secrets (masked by `read_file()`, must use `Python open()`)
- `AGENT_ID`, `OPENCLAW_AGENT_NAME` — instance identity
- `HERMES_HOME` — overrides default `~/.hermes`
## Data Flow Discipline
### State Architecture
- **Instance state is sole truth:** `skills/ETF_TW/instances/<agent_id>/state/`
- **Root `ETF_TW/state/` is legacy** — do NOT read from it for production logic
- **Downstream summaries must NEVER overwrite upstream truth:** `agent_summary.json` and `intraday_tape_context.json` are display layer
### Refresh Pipeline Order (Must Be Sequential)
## Response Format
### Strategy Header (Mandatory)
### Trading Hours Gate
- General: 09:00–13:30
- After-hours odd lot: 13:40–14:30
- Outside hours: Reply "現在非交易時段，無法下單" — no submission attempt
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Instance state as single source of truth (multi-tenant isolation)
- File-based JSON/JSONL state with atomic writes
- Broker adapter pattern (Strategy pattern) for multi-broker support
- Staged autonomy: rule engine + AI bridge with tiered consensus arbitration
- Sequential refresh pipeline with strict ordering
- 4-layer precedence model for broker order reconciliation
- Separation of truth layer (positions/orders) from display layer (summaries)
## Layers
- Purpose: Web UI for portfolio, orders, AI suggestions, health monitoring
- Location: `skills/ETF_TW/dashboard/`
- Contains: FastAPI app, Jinja2 templates, API endpoints
- Depends on: Instance state files (read-only), `etf_core/context.py`, reconciliation helpers
- Used by: Human operator via browser (port 5055)
- Purpose: Generate trading decisions from market data and portfolio state
- Location: `skills/ETF_TW/scripts/ai_decision_bridge.py`, `scripts/run_auto_decision_scan.py`, `scripts/generate_ai_decision_response.py`, `scripts/generate_ai_agent_response.py`
- Contains: Request/Response builders, consensus resolver, provenance logger
- Depends on: Refresh pipeline outputs (all state files)
- Used by: Dashboard (displays suggestions), Cron jobs (triggers scans)
- Purpose: Sequentially sync and enrich state from external data sources
- Location: `skills/ETF_TW/scripts/sync_*.py`, `scripts/generate_*.py`, `scripts/check_major_event_trigger.py`
- Contains: 10 ordered scripts that build the complete market/policy picture
- Depends on: Shioaji API, yfinance, instance config, broker adapters
- Used by: Cron jobs, manual triggers, dashboard refresh API
- Purpose: Validate, preview, and submit orders through broker adapters
- Location: `skills/ETF_TW/scripts/complete_trade.py`, `scripts/preview_order.py`, `scripts/validate_order.py`, `scripts/risk_controller.py`
- Contains: Order lifecycle, trading hours gate, venv executor, fee/tax calculation
- Depends on: Broker adapters, risk controller, trading mode state
- Used by: Agent commands, auto-trade scan (paper mode)
- Purpose: Abstract broker-specific APIs behind a common interface
- Location: `skills/ETF_TW/scripts/adapters/base.py`, `scripts/adapters/paper_adapter.py`, `scripts/adapters/sinopac_adapter.py`, `scripts/adapters/cathay_adapter.py`, `scripts/adapters/yuanlin_adapter.py`
- Contains: `BaseAdapter` ABC with `Order`, `Position`, `AccountBalance` dataclasses; `get_adapter()` factory
- Depends on: shioaji SDK (sinopac), yfinance (market data fallback)
- Used by: `account_manager.py`, `complete_trade.py`, `sync_live_state.py`
- Purpose: Single source of truth for all runtime data
- Location: `skills/ETF_TW/instances/<agent_id>/state/` (e.g., `instances/etf_master/state/`)
- Contains: 27+ JSON and JSONL files; append-only journals, atomic-overwrite snapshots
- Depends on: Nothing (root truth layer)
- Used by: All layers above (read); refresh pipeline and execution layer (write)
- Purpose: Shared infrastructure for state I/O, schema validation, path resolution
- Location: `skills/ETF_TW/scripts/etf_core/context.py`, `scripts/etf_core/state_io.py`, `scripts/etf_core/state_schema.py`
- Contains: `get_state_dir()`, `get_instance_dir()`, `safe_load_json()`, `atomic_save_json()`, `safe_append_jsonl()`, `validate_state_payload()`
- Depends on: `AGENT_ID` / `OPENCLAW_AGENT_NAME` env vars
- Used by: Every script in the project
## Data Flow
- **JSON files**: Atomic overwrite via `atomic_save_json()` (write temp + rename)
- **JSONL files**: Append-only via `safe_append_jsonl()` (audit trail -- decisions, provenance, outcomes)
- **Schema validation**: `validate_state_payload()` checks required keys per state kind
- **Downstream protection**: Display summaries (`agent_summary.json`, `intraday_tape_context.json`) MUST NOT overwrite truth files (`positions.json`, `orders_open.json`, `account_snapshot.json`)
## Key Abstractions
- Purpose: Abstract all broker-specific APIs behind a uniform interface
- Examples: `scripts/adapters/base.py` (BaseAdapter), `scripts/adapters/sinopac_adapter.py` (SinopacAdapter), `scripts/adapters/paper_adapter.py` (PaperAdapter)
- Pattern: Strategy pattern with ABC; `get_adapter()` factory dispatches by `broker_id`; new brokers subclass BaseAdapter, implement 7 abstract methods (`authenticate`, `get_market_data`, `get_account_balance`, `get_positions`, `preview_order`, `validate_order`, `submit_order`, `cancel_order`, `get_order_status`)
- Purpose: Resolve conflicts when multiple sources update the same order
- Examples: `scripts/order_event_precedence.py` (`choose_preferred_row()`), `scripts/order_event_bridge.py` (`event_payload_to_order_row()`)
- Pattern: 4-layer deterministic comparison: (1) status rank (terminal states cannot be overwritten), (2) timestamp precedence (`event_time` > `observed_at`), (3) `broker_seq` (higher wins), (4) source priority (callback=4 > polling=3 > verification=2 > response=1 > inference=0)
- Purpose: Merge deterministic rule engine with probabilistic AI bridge
- Examples: `scripts/run_auto_decision_scan.py` (`resolve_consensus()`)
- Pattern: Three-tier arbitration: Tier 1 (both agree on symbol + direction = high confidence, execute), Tier 2 (disagreement = rule engine has veto, medium confidence), Tier 3 (opposite directions on same symbol = locked, requires human)
- Purpose: Append-only audit trail for every decision cycle
- Examples: `scripts/provenance_logger.py` (`build_provenance_record()`, `append_provenance()`)
- Pattern: One JSONL record per decision with `inputs_digest` (compressed market context), `outputs` (action/symbol/confidence), and `review_lifecycle` (T1/T3/T10 back-fill slots); records are never deleted or overwritten
- Purpose: Formal request/response protocol between dashboard/scripts and AI agent
- Examples: `scripts/ai_decision_bridge.py` (`build_ai_decision_request()`, `build_ai_decision_response()`, `is_ai_decision_response_stale()`)
- Pattern: Request artifact (`ai_decision_request.json`) aggregates 15 input sources (market data, positions, strategy, worldmonitor, wiki × 4, etc.); Response artifact (`ai_decision_response.json`) includes `expires_at`, `stale` flag, `confidence`, `uncertainty`, `strategy_alignment`, and `input_refs` for traceability; freshness tracked via ISO timestamps with `Asia/Taipei` timezone
- Purpose: Route all path resolution through instance-aware functions
- Examples: `scripts/etf_core/context.py` (`get_instance_id()`, `get_state_dir()`, `get_instance_dir()`, `get_instance_config()`, `get_broker_config()`)
- Pattern: All state paths derived from `AGENT_ID` env var; auto-creates directory structure; singleton warning for missing env var
## Entry Points
- Location: `skills/ETF_TW/scripts/etf_tw.py`
- Triggers: Hermes agent commands, shell invocation via `.venv/bin/python3 scripts/etf_tw.py <command>`
- Responsibilities: ETF list/search/filter, comparison, DCA calculation, order preview/validation/paper trading, multi-broker account management
- Location: `skills/ETF_TW/dashboard/app.py`
- Triggers: `.venv/bin/python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 5055`
- Responsibilities: FastAPI web server; strategy update API, auto-trade config API, order submission API, health monitoring, reconciliation alerts, refresh triggers
- Location: `skills/ETF_TW/scripts/venv_executor.py`
- Triggers: Hermes agent executing scripts from possibly wrong Python environment
- Responsibilities: Forces all script execution through `.venv/bin/python3` to prevent "live order from wrong env" incidents
- Location: `skills/ETF_TW/scripts/run_auto_decision_scan.py`
- Triggers: Cron jobs (`ETF 早班準備`, `ETF 健康巡檢`), manual invocation
- Responsibilities: Runs rule engine evaluation + AI bridge consensus, writes preview candidates, logs provenance
- Location: `skills/ETF_TW/scripts/sync_*.py`, `scripts/generate_*.py`, `scripts/check_major_event_trigger.py`
- Triggers: Cron jobs (08:00 pre-market), manual refresh, dashboard refresh API
- Responsibilities: Pull external data, compute derived context, write instance state files in strict sequential order
- Location: `skills/ETF_TW/scripts/layered_review_cron_registry_live.py`
- Triggers: Cron (daily, post-market)
- Responsibilities: T+1 / T+3 / T+10 review of past AI decisions; back-fills `ai_decision_outcome.jsonl` and `ai_decision_review.jsonl`
## Error Handling
- **Trading hours gate**: Hard exit (`sys.exit(1)`) when order attempted outside 09:00-13:30 / 13:40-14:30; function `is_trading_hours()` returns boolean for non-fatal checks
- **State I/O safety**: `safe_load_json()` returns default on any failure; `atomic_save_json()` uses temp file + rename to prevent corruption
- **AI Bridge fallback**: If AI is unavailable/stale, dashboard displays last valid response with stale badge; falls back to rule engine preview
- **Ghost order detection**: `broker_order_id: null` + `verified: false` + `order_id: ""` = phantom order; never reported as placed
- **Adapter import guards**: `try/except ImportError` around shioaji, yfinance, optional adapters (cathay, yuanlin)
- **DNS fix injection**: `dns_fix.py` patch applied at top of `run_auto_decision_scan.py` for sandbox environment compatibility
- **Provenance append-only**: Decision logs never deleted; `safe_append_jsonl()` uses `os.fsync()` for durability
- **Partial fill monotonicity**: `filled_quantity` can only advance, never retreat; enforced in `choose_preferred_row()`
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
