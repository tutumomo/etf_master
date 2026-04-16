# Codebase Structure

**Analysis Date:** 2025-05-22

## Directory Layout

```
[profile-root]/
├── assets/         # Configuration and examples
├── bin/            # Binaries (tirith)
├── cron/           # Cron jobs and output
├── data/           # Static data (ETFs, brokers)
├── docs/           # Documentation and Wiki
├── logs/           # System logs
├── plans/          # Execution plans
├── scripts/        # Orchestration and sync scripts
└── skills/
    └── ETF_TW/     # Core skill logic
        ├── data/   # Skill-specific data
        ├── instances/ etf_master/ state/ # Runtime state
        ├── scripts/ # Primary Python scripts
        │   ├── adapters/ # Broker-specific implementations
        │   └── etf_core/ # Shared core library
        └── tests/   # Test suite
```

## Directory Purposes

**scripts/ (profile root):**
- Purpose: High-level orchestration.
- Key files: `generate_decision_consensus.py`.

**skills/ETF_TW/scripts/:**
- Purpose: Core logic for the ETF_TW skill.
- Key files: `etf_tw.py`, `pre_flight_gate.py`, `submit_verification.py`.

**skills/ETF_TW/scripts/adapters/:**
- Purpose: Broker-specific API abstractions.
- Key files: `base.py`, `sinopac_adapter.py`.

**skills/ETF_TW/instances/etf_master/state/:**
- Purpose: Truth source and inter-component communication state.
- Key files: `portfolio_snapshot.json`, `ai_decision_response.json`, `auto_trade_state.json`.

## Key File Locations

**Entry Points:**
- `skills/ETF_TW/scripts/etf_tw.py`: Primary CLI.
- `skills/ETF_TW/scripts/run_auto_decision_scan.py`: Rule Engine entry.

**Configuration:**
- `assets/config.json`: Master configuration.
- `data/brokers.json`: Broker directory.

**Core Logic:**
- `skills/ETF_TW/scripts/etf_core/main_service.py`: Backend service logic.
- `skills/ETF_TW/scripts/pre_flight_gate.py`: Safety gate.

**Testing:**
- `skills/ETF_TW/tests/`: Directory containing all unit and integration tests.

## Naming Conventions

**Files:**
- [Python Scripts]: snake_case.py (e.g., `pre_flight_gate.py`).
- [Tests]: test_*.py (e.g., `test_trade_validation.py`).

**Directories:**
- [Modules]: snake_case.
- [State Instances]: snake_case.

## Where to Add New Code

**New Broker Adapter:**
- Implementation: `skills/ETF_TW/scripts/adapters/` (inherit from `BaseAdapter`).
- Registration: `skills/ETF_TW/scripts/adapters/base.py:get_adapter`.

**New Sync Script:**
- Implementation: `skills/ETF_TW/scripts/sync_*.py`.

**New Trading Logic / Validation:**
- Implementation: `skills/ETF_TW/scripts/pre_flight_gate.py` (or a dedicated script called by it).

**Utilities:**
- Shared helpers: `skills/ETF_TW/scripts/etf_core/utils/`.

## Special Directories

**state/:**
- Purpose: Ephemeral but critical runtime state.
- Generated: Yes.
- Committed: Generally not (contains user trade data).

---

*Structure analysis: 2025-05-22*
