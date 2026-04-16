# External Integrations

**Analysis Date:** 2025-05-22

## APIs & External Services

**Market Data:**
- Yahoo Finance (yfinance) - Historical and intraday prices.
- Shioaji (SinoPac SDK) - Real-time market data and order placement.

**Execution:**
- Shioaji API - Order submission (`submit_order`), order status tracking (`list_trades`), account balance (`get_account_balance`).

## Data Storage

**Databases:**
- SQLite (implicitly in `etf_core/db/database.py`) - Persistent storage for trades and data logs.
- JSON-based State Files - Primary interface for the dashboard and agent coordination.

**File Storage:**
- `skills/ETF_TW/instances/etf_master/state/` - Core runtime state artifacts.

**Caching:**
- `market_cache.json` - Temporary storage for market quotes.

## Authentication & Identity

**Auth Provider:**
- Custom (Token-based/Certificate-based).
- Shioaji requires a `CA Certificate` and user credentials for Live mode.
- Authentication implemented in `adapters/sinopac_adapter.py`.

## Monitoring & Observability

**Error Tracking:**
- Local log files (`shioaji.log`, `logs/agent.log`).

**Logs:**
- `provenance_logger.py` - Tracks decision provenance.
- `trade_logger.py` - Dedicated trade event logging.

## CI/CD & Deployment

**Hosting:**
- Local execution on Hermes instance.

**CI Pipeline:**
- None detected in this repository.

## Environment Configuration

**Required env vars:**
- None specified (configuration primarily via `assets/config.json`).

**Secrets location:**
- `assets/config.json` (Note: Never read or quote its contents).

## Multi-Skill Integration

**stock-analysis-tw:**
- Orchestration level integration via LLM instructions.
- Provides "8-Dimension" depth diagnosis and scoring.
- Refers to shared `state/` files for contextual awareness.

**stock-market-pro-tw:**
- Orchestration level integration.
- Provides professional technical charts (PNG output).
- Consults `ETF_TW` for current truth (positions/orders).

---

*Integration audit: 2025-05-22*
