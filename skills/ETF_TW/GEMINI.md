# ETF_TW: Taiwan ETF Investing Assistant

`ETF_TW` is a comprehensive investment assistant for Taiwan Exchange-Traded Funds (ETFs). It provides research, comparison, simulation (paper trading), and risk-control capabilities, with an integrated dashboard and support for major Taiwanese brokers via the Shioaji (SinoPac) API.

## Project Overview

- **Purpose:** Assist users in Taiwan ETF research, risk management, and trading execution.
- **Key Technologies:**
  - **Language:** Python 3.x
  - **Market Data:** Yahoo Finance (via `yfinance`), Shioaji (SinoPac API).
  - **Architecture:** Multi-broker adapter pattern (`paper`, `sinopac`, `cathay`, `yuanlin`).
  - **State Management:** JSON-based state tracking in the `state/` directory.
  - **Visualization:** Flask-based Dashboard for portfolio and risk monitoring.
- **Core Modules:**
  - `scripts/etf_tw.py`: Main CLI entry point.
  - `scripts/adapters/`: Broker-specific implementations.
  - `scripts/etf_core/`: Shared business logic, database (SQLite), and simulation engine.
  - `dashboard/`: Web interface for portfolio overview and trading mode management.

## Getting Started

### Prerequisites
- Python 3.8+
- Recommended: A virtual environment (`.venv`).

### Installation
1.  **Initialize Environment:**
    ```bash
    python scripts/etf_tw.py init --install-deps
    ```
2.  **Check Dependencies:**
    ```bash
    python scripts/etf_tw.py check
    ```

## Key Commands

### Research & Analysis
- **List/Search ETFs:**
  ```bash
  python scripts/etf_tw.py list
  python scripts/etf_tw.py search <keyword>
  ```
- **Compare ETFs:**
  ```bash
  python scripts/etf_tw.py compare 0050 006208
  ```
- **DCA (Regular Savings) Calculator:**
  ```bash
  python scripts/etf_tw.py calc 0050 10000 10 --annual-return 0.07
  ```

### Trading & Operations
- **Portfolio Overview:**
  ```bash
  python scripts/etf_tw.py portfolio
  ```
- **Mode Management:**
  - Check status: `python scripts/etf_tw.py mode status`
  - Switch to Paper: `python scripts/etf_tw.py mode paper`
  - Switch to Live: `python scripts/etf_tw.py mode live`
- **Execute Paper Trade:**
  ```bash
  python scripts/etf_tw.py paper-trade --symbol 0050 --side buy --quantity 100 --price 185
  ```

### Dashboard
- **Start Dashboard:**
  ```bash
  bash scripts/start_dashboard.sh
  ```
  Access via `http://localhost:5000` (default).

## Development Conventions

- **Trading Modes:**
  - `paper`: Default. No real money used. Uses `paper_ledger.json`.
  - `live`: Real trading using Shioaji (SinoPac). Requires valid credentials in `assets/config.json`.
- **Live Truth Source:** For Live mode, stock quantity **MUST** be fetched using `Shioaji list_positions(..., unit=Unit.Share)`. Never use `Unit.Common` for live balances.
- **Unit Safety:** Always verify "shares" (股) vs "lots" (張, 1 lot = 1000 shares) during order validation to prevent accidents.
- **State Synchronization:** Use `scripts/sync_*.py` scripts to keep the dashboard and state files in sync with broker data.
- **Testing:** New features should include tests in the `tests/` directory. Run tests using `pytest`.

## Directory Structure Highlights
- `assets/`: Configuration (`config.json`) and dependencies.
- `data/`: Static data (ETF definitions, broker registries) and local ledgers.
- `state/`: Dynamic runtime state (mode, snapshots, order logs).
- `scripts/`: Implementation logic and adapters.
- `references/`: Detailed documentation on risk controls, onboarding, and workflows.
