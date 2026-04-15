# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python 3.14.3 — All skill implementations, automation scripts, dashboard, broker adapters, test suite
- YAML — Configuration (`config.yaml`), skill manifests (`SKILL.md` frontmatter), skin themes
- JSON — State files, broker registry, ETF universe, trade logs, instance configuration
- HTML/Jinja2 — Dashboard templates (`dashboard/templates/base.html`, `dashboard/templates/overview.html`)

**Secondary:**
- Markdown — Reference docs, SOUL.md, AGENTS.md, wiki pages
- Shell — Dashboard startup script (`scripts/start_dashboard.sh`)
- SQL (SQLite dialect) — Session database (`state.db`), legacy ETF_TW database (`etf_core/db/etf_tw.db`)

## Runtime

**Environment:**
- Python 3.14.3 — Dedicated venv at `skills/ETF_TW/.venv/`
- Hermes Agent v0.9.0 — Core agent framework (installed at `~/.hermes/hermes-agent/`)

**Package Manager:**
- pip (via venv) — ETF_TW and all skill dependencies
- uv — Stock-analysis-tw and stock-market-pro-tw scripts use `uv run --script` inline dependency declarations
- Lockfile: Not present (no poetry.lock or requirements.lock)

## Frameworks

**Core:**
- FastAPI 0.135.2 — Dashboard REST API (20 endpoints) at `skills/ETF_TW/dashboard/app.py`
- Uvicorn 0.42.0 — ASGI server for dashboard (port 5055)
- Pydantic 2.12.3 — Request/response models for dashboard API, config validation
- Starlette 1.0.0 — Underlying FastAPI web framework

**Testing:**
- pytest 9.0.2 — Test runner; 145 test files in `skills/ETF_TW/tests/`

**Build/Dev:**
- Hermes Agent CLI (`hermes`) — Agent management, model switching, gateway, config
- Jinja2 3.1.6 — Template rendering for dashboard HTML

## Key Dependencies

**Critical:**
- shioaji 1.3.2 — SinoPac Securities (永豐金證券) Python SDK for live trading
- yfinance 1.2.0 — Yahoo Finance market data (quotes, OHLCV, fundamentals)
- pandas 3.0.1 — Data manipulation for price analysis, OHLCV processing
- numpy 2.4.3 — Numerical computations, technical indicator calculations
- peewee 4.0.2 — ORM for legacy database operations in `etf_core/db/`

**Infrastructure:**
- httpx 0.28.1 — Async HTTP client (Hermes core)
- requests 2.32.5 — Synchronous HTTP for RSS feeds, LLM API calls, news crawling
- beautifulsoup4 4.14.3 — HTML parsing for web scraping
- feedparser 6.0.12 — RSS/Atom feed parsing for news collection
- loguru 0.7.3 — Structured logging
- rich 14.3.3 — Terminal formatting and tables
- orjson 3.11.7 — Fast JSON serialization
- sentry-sdk 2.55.0 — Error tracking (installed in venv, integration usage TBD)

**Visualization:**
- matplotlib — Stock chart rendering (stock-market-pro-tw)
- mplfinance — Candlestick/financial chart plotting (stock-market-pro-tw)
- plotille — Terminal ASCII charts (stock-market-pro-tw)

## Configuration

**Environment:**
- Hermes profile config: `config.yaml` — model, display, tools, memory, terminal, privacy
- Agent persona: `SOUL.md` — risk-first investment assistant rules
- Instance config: `skills/ETF_TW/instances/etf_master/instance_config.json` — broker accounts, credentials (private)
- Environment vars: `.env` file present at profile root — contains API keys and secrets (NEVER read contents)
- Shell env vars for instance identity: `AGENT_ID`, `OPENCLAW_AGENT_NAME`

**Build:**
- ETF_TW venv: `skills/ETF_TW/.venv/` — isolated Python with all trading dependencies
- Dashboard: `uvicorn dashboard.app:app --host 0.0.0.0 --port 5055`
- Skills use `uv run --script` with inline PEP 723 dependency declarations

## Platform Requirements

**Development:**
- macOS (Darwin 25.0.0) — Current development platform
- Python 3.14+ required for ETF_TW venv
- Hermes Agent v0.9.0 installed system-wide
- Internet access for yfinance, RSS feeds, LLM APIs

**Production:**
- Hermes Agent runtime (local or containerized)
- SinoPac Securities account for live trading (optional)
- Dashboard served via uvicorn on port 5055
- Cron scheduler for market scanning (weekday schedules)

---

*Stack analysis: 2026-04-15*