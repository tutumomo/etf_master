# Technology Stack

**Analysis Date:** 2025-05-22

## Languages

**Primary:**
- Python 3.x - Core logic, CLI, and adapters. Uses `asyncio` for asynchronous I/O (API calls).

**Secondary:**
- Shell (Bash) - Setup and dashboard launch scripts.

## Runtime

**Environment:**
- Node.js (implicitly, for Hermes/Gemini environment if applicable, but project is Python-centric)
- Python Virtual Environment (.venv)

**Package Manager:**
- pip
- Lockfile: `skills/ETF_TW/scripts/etf_core/requirements.txt` (present)

## Frameworks

**Core:**
- Shioaji (SinoPac API) - Primary brokerage integration for Taiwan market.
- yfinance - Secondary market data source.
- Flask (implicitly, for Dashboard as mentioned in `GEMINI.md`).

**Testing:**
- Pytest - Testing framework used in `tests/` directory.

**Build/Dev:**
- argparse - CLI argument parsing in `etf_tw.py`.

## Key Dependencies

**Critical:**
- `shioaji` - Professional brokerage API for Taiwan stocks/ETFs.
- `yfinance` - Reliable fallback for historical and intraday market data.
- `pandas` / `numpy` - Data processing and technical indicators calculation.

**Infrastructure:**
- `zoneinfo` - Timezone handling for Taiwan market hours (`Asia/Taipei`).
- `json` / `pathlib` - State management and file I/O.

## Configuration

**Environment:**
- Local config: `assets/config.json`.
- Account data: `data/brokers.json`.
- Credentials: Local `config.json` (contains API keys/secrets).

**Build:**
- `scripts/setup_agent.py` - Instance initialization.
- `scripts/etf_tw.py init` - Environment setup.

## Platform Requirements

**Development:**
- Python 3.8+
- SinoPac (Shioaji) account and CA certificate (for Live mode).

**Production:**
- Linux/macOS with network access to Taiwan market data providers.

---

*Stack analysis: 2025-05-22*
