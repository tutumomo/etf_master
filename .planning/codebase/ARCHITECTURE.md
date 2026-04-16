# Architecture

**Analysis Date:** 2025-05-22

## Pattern Overview

**Overall:** Multi-Broker Adapter Pattern with Decision Double-Chain Arbitration.

**Key Characteristics:**
- **Separation of Concerns:** Business logic (`scripts/`) is separated from broker interaction (`scripts/adapters/`).
- **State-Driven Orchestration:** The dashboard and LLM agents interact via JSON state files in the `state/` directory.
- **Truth Layering:** Explicitly distinguishes between "Snapshot" (fast) and "Live/Verified" (slow, authoritative) truth levels.

## Layers

**Execution Layer:**
- Purpose: Handles order submission and broker-specific APIs.
- Location: `skills/ETF_TW/scripts/adapters/`
- Contains: `base.py`, `sinopac_adapter.py`, `paper_adapter.py`.
- Depends on: `pre_flight_gate.py`, `submit_verification.py`.
- Used by: `etf_tw.py`, `complete_trade.py`.

**Validation Layer (FUSE-02):**
- Purpose: Unified safety checks before order submission.
- Location: `skills/ETF_TW/scripts/pre_flight_gate.py`
- Contains: `check_order` function.
- Depends on: `sizing_engine_v1.py`, `trading_hours_gate.py`.
- Used by: `BaseAdapter.submit_order`.

**Decision Layer (Double-Chain):**
- Purpose: Generates trading signals from Rule Engine and AI.
- Location: `skills/ETF_TW/scripts/`
- Contains: `run_auto_decision_scan.py` (Rules), `generate_ai_decision_request.py` (AI).
- Depends on: `ai_decision_bridge.py`, `ai_decision_memory_context.py`.
- Used by: `generate_decision_consensus.py` (Arbitration).

**Core Logic Layer:**
- Purpose: Shared utilities, database, and state management.
- Location: `skills/ETF_TW/scripts/etf_core/`
- Contains: `state_io.py`, `main_service.py`, `broker_manager.py`.

## Data Flow

**Trading Chain Flow:**
1.  `etf_tw.py` (CLI) → `BaseAdapter.submit_order` (Universal Gate).
2.  `BaseAdapter` calls `pre_flight_gate.py:check_order` for FUSE-02 safety checks.
3.  On success, `BaseAdapter` calls `_submit_order_impl` (Broker-specific).
4.  After submission, `submit_verification.py:verify_order_landing` polls `list_trades` until verified.

**Decision Arbitration Flow:**
1.  `run_auto_decision_scan.py` runs rule-based scoring (TOMO principles).
2.  `generate_ai_decision_request.py` packs state files for LLM analysis.
3.  `generate_decision_consensus.py` reads both outputs and arbitrates conflict (BUY/SELL/HOLD/LOCKED).

**State Management:**
- Synchronous reading/writing of JSON files in `instances/etf_master/state/`.
- Atomic writes implemented in `etf_core/state_io.py:atomic_save_json`.

## Key Abstractions

**BaseAdapter:**
- Purpose: Standardized interface for all brokers.
- Examples: `scripts/adapters/base.py`
- Pattern: Abstract Base Class.

**Order / Position / AccountBalance:**
- Purpose: Common data structures for trading information.
- Examples: `scripts/adapters/base.py`
- Pattern: Dataclass.

## Entry Points

**etf_tw.py:**
- Location: `skills/ETF_TW/scripts/etf_tw.py`
- Triggers: User CLI commands.
- Responsibilities: Routing, account management, portfolio overview.

**run_auto_decision_scan.py:**
- Location: `skills/ETF_TW/scripts/run_auto_decision_scan.py`
- Triggers: Cron or periodic scan.
- Responsibilities: Rule-based signal generation and arbitration.

## Error Handling

**Strategy:** Fail-fast at the pre-flight gate. Silent retry for post-submit verification until timeout.

**Patterns:**
- **Gate Blocking:** If `pre_flight_gate` fails, order status becomes `rejected` with detailed reason.
- **Truth Verification:** Orders are only considered "landed" after being confirmed by `list_trades` (LEVEL_1_LIVE).

## Cross-Cutting Concerns

**Logging:** `provenance_logger.py` and standard Python logging (`shioaji.log`).
**Validation:** Centralized in `pre_flight_gate.py` and `etf_core/state_schema.py`.
**Authentication:** Managed per-adapter via `authenticate()` method.

---

*Architecture analysis: 2025-05-22*
