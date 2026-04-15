# Coding Conventions

**Analysis Date:** 2026-04-15

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
Tests and scripts use `importlib.util` for loading scripts as modules:
```python
import importlib.util, sys
sys.path.insert(0, "/path/to/scripts")
spec = importlib.util.spec_from_file_location("module_name", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```
This is because scripts under `scripts/` are not in a proper Python package.

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
1. **Status rank:** Terminal states (filled/cancelled/rejected) cannot be overwritten
2. **Timestamp precedence:** `event_time` > `observed_at`
3. **broker_seq precedence:** Higher wins
4. **Source priority:** callback(4) > polling(3) > submit_verification(2) > submit_response(1) > local_inference(0)
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
1. `sync_strategy_link.py` → 2. `sync_live_state.py`/`sync_paper_state.py` → 3. `sync_market_cache.py` → 4. `generate_market_event_context.py` → 5. `generate_taiwan_market_context.py` → 6. `check_major_event_trigger.py` → 7. `sync_portfolio_snapshot.py` → 8. `sync_ohlcv_history.py` → 9. `generate_intraday_tape_context.py` → 10. `sync_agent_summary.py`

## Response Format

### Strategy Header (Mandatory)
Every AI reply must prefix with: `[目前投資策略:XXX, 情境覆蓋:YYY]` from `strategy_link.json`

### Trading Hours Gate
- General: 09:00–13:30
- After-hours odd lot: 13:40–14:30
- Outside hours: Reply "現在非交易時段，無法下單" — no submission attempt

---

*Conventions analysis: 2026-04-15*