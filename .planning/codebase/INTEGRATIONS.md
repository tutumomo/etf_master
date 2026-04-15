# External Integrations

**Analysis Date:** 2026-04-15

## Trading APIs

### SinoPac Securities (永豐金證券) — Shioaji SDK
- **Library:** `shioaji 1.3.2`
- **Purpose:** Live order placement, position queries, account snapshot, order status polling
- **Adapter:** `skills/ETF_TW/scripts/adapters/sinopac_adapter.py` (basic), `sinopac_adapter_enhanced.py` (extended)
- **Auth:** API key + secret key stored in `instance_config.json`, login via `api.login()`
- **Key patterns:**
  - `api.stock_account` is a **property** — never call with `()`
  - `api.logout()` **segfaults** — never call it
  - Broker order ID: `trade.order.ordno` (NOT `trade.status.order_id`)
  - TSE ETFs: `api.Contracts.Stocks.TSE.TSE0050`
  - OTC ETFs: `api.Contracts.Stocks.OTC.get('00679B')`

### Paper Trading (Built-in)
- **Adapter:** `skills/ETF_TW/scripts/adapters/paper_adapter.py`
- **Purpose:** Simulated order execution for testing strategies without real money
- **Behavior:** Mirrors sinopac_adapter interface, tracks state in `paper_state/`

### Additional Brokers (Registered but may be incomplete)
- Cathay (`cathay_adapter.py`)
- Yuanlin (`yuanlin_adapter.py`)
- **Registry:** `skills/ETF_TW/data/broker_registry.json`

## Market Data APIs

### Yahoo Finance — yfinance
- **Library:** `yfinance 1.2.0`
- **Purpose:** Historical OHLCV, real-time quotes, dividend data, fundamentals
- **Used in:** `sync_market_cache.py`, `sync_ohlcv_history.py`, `diag_probe.py`, `etf_tw.py`
- **Ticker convention:** Most ETFs use `.TW` suffix; TPBS-listed (prefix 006) use `.TWO`
- **Rate limits:** No official rate limit but aggressive polling triggers 429s

### RSS/News Feeds
- **Library:** `feedparser 6.0.12`
- **Purpose:** Parse RSS/Atom feeds for market news
- **Sources:** `skills/ETF_TW/scripts/sync_news_from_rss.py`, `scripts/etf_core/utils/news_crawler.py`
- **HTTP client:** `requests 2.32.5` for fetching feed content

## LLM/AI APIs

### LLM Decision Reasoning
- **Endpoint:** Configured via `instance_config.json` or env vars
- **Purpose:** AI-augmented investment decision generation
- **Scripts:** `generate_llm_decision_reasoning.py`, `generate_ai_agent_response.py`
- **HTTP client:** `requests` for synchronous LLM API calls
- **Context:** Feeds from market intelligence, positions, agent summary

### AI Decision Bridge
- **File:** `skills/ETF_TW/scripts/ai_decision_bridge.py`
- **Purpose:** Stage-based AI autonomy (Stage 0-3)
- **Contract files:** `ai_decision_request.json`, `ai_decision_response.json`, `ai_decision_outcome.jsonl`, `ai_decision_review.jsonl`

## Web Scraping

### News Crawling
- **Library:** `beautifulsoup4 4.14.3` + `requests 2.32.5`
- **File:** `skills/ETF_TW/scripts/etf_core/utils/news_crawler.py`
- **Purpose:** Parse financial news sites for market context
- **Also:** `sync_news_from_local.py` for local news sources

## HTTP Infrastructure

### Hermes Agent Core
- **Library:** `httpx 0.28.1` — async HTTP client for agent-to-agent communication
- **Library:** `requests 2.32.5` — synchronous HTTP for external APIs within ETF_TW

### Dashboard Server
- **Framework:** FastAPI 0.135.2 on Uvicorn 0.42.0
- **Port:** 5055
- **Endpoints:** ~20 REST endpoints for portfolio, orders, positions, market data, AI decisions
- **Entry:** `skills/ETF_TW/dashboard/app.py`

## Data Storage

### SQLite
- **Hermes sessions:** `~/.hermes/sessions/state.db` (FTS5 full-text search)
- **ETF_TW legacy:** `skills/ETF_TW/etf_core/db/etf_tw.db` (ORM via peewee 4.0.2)

### JSON/JSONL State Files
- **Instance state:** `skills/ETF_TW/instances/<agent_id>/state/*.json`
  - `positions.json`, `account_snapshot.json`, `orders_open.json`
  - `ai_decision_request.json`, `ai_decision_response.json`
- **Append-only logs:** `*.jsonl` files for outcomes and reviews

## Error Tracking

### Sentry
- **Library:** `sentry-sdk 2.55.0`
- **Status:** Installed in venv but integration usage is TBD

---

*Integration analysis: 2026-04-15*