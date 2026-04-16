# Codebase Concerns

**Analysis Date:** 2025-05-22

## Tech Debt

**[State File Redundancy]:**
- Issue: `run_auto_decision_scan.py` and `generate_decision_consensus.py` both have arbitration logic. There is risk of logic drift between the two.
- Files: `run_auto_decision_scan.py`, `generate_decision_consensus.py`.
- Impact: Inconsistent consensus results between the background scan and the dashboard.
- Fix approach: Unify arbitration logic into a single module or service.

## Known Bugs

**[None detected]:** 
- Symptoms: No immediate runtime errors found during static analysis.

## Security Considerations

**[Secret Management]:**
- Risk: Credentials (API keys, secrets) are stored in `assets/config.json`. If this file is committed, secrets are leaked.
- Files: `assets/config.json`.
- Current mitigation: `.gitignore` usually handles this (not confirmed).
- Recommendations: Ensure `.gitignore` explicitly excludes `config.json` or use environment variables/secret management services.

## Performance Bottlenecks

**[Post-Submit Polling]:**
- Problem: `verify_order_landing.py` uses active polling with `asyncio.sleep(1)` for 10 seconds.
- Files: `submit_verification.py`.
- Cause: Synchronous check for "landing" fact in `list_trades`.
- Improvement path: Switch to websocket-based order callbacks if supported by the broker API (Shioaji supports this).

## Fragile Areas

**[Manual Path Manipulation]:**
- Files: Multiple scripts (e.g., `run_auto_decision_scan.py`, `generate_ai_decision_request.py`).
- Why fragile: Heavy use of `sys.path.insert(0, ...)` and `ROOT` calculation based on file location.
- Safe modification: Standardize project layout and use a `pyproject.toml` or `PYTHONPATH`.

## Scaling Limits

**[State File Synchronization]:**
- Current capacity: Efficient for small portfolios.
- Limit: With many symbols (>100) or high-frequency updates, JSON file contention may occur.
- Scaling path: Move to a proper database (PostgreSQL/Redis) for high-frequency state updates.

## Missing Critical Features

**[Automated Live Trading Gate]:**
- Problem: Currently, there is a "LOCKED" state in consensus, but no automated "Submit" path that is fully de-risked.
- Blocks: Fully autonomous trading (though this is a deliberate safety choice).

## Test Coverage Gaps

**[Adapter Mocks]:**
- What's not tested: Real broker API error scenarios (network timeout, API maintenance).
- Files: `adapters/sinopac_adapter.py`.
- Risk: Unhandled API exceptions during live trading.
- Priority: High.

---

*Concerns audit: 2025-05-22*
