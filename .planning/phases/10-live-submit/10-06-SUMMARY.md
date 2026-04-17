---
phase: 10-live-submit
plan: "06"
subsystem: Tests
tags: [regression, live-submit, ghost-detection, pre-flight-gate, LIVE-03]
dependency_graph:
  requires: [10-04, 10-05]
  provides: [LIVE-03 regression coverage]
  affects: [live_submit_sop.py, test_live_submit_regression.py]
tech_stack:
  added: []
  patterns: [asyncio.run + AsyncMock, tmp_path isolation, monkeypatch fixture]
key_files:
  created:
    - skills/ETF_TW/tests/test_live_submit_regression.py
  modified:
    - skills/ETF_TW/scripts/live_submit_sop.py
decisions:
  - "Order dataclass lacks broker_order_id field; used MagicMock() for submitted_order instead of real Order instance"
  - "live_submit_sop.py had no deduplication guard; added order_id existence check before appending to orders_open.json (Rule 2)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-17"
  tasks_completed: 1
  files_changed: 2
---

# Phase 10 Plan 06: Live Submit Regression Tests Summary

7 項回歸測試涵蓋完整 live submit pipeline（幽靈委託/閘門攔截/例外處理/去重）。

## One-liner

LIVE-03 regression suite: 7 tests covering ghost detection, gate blocking, adapter exceptions, double-submit deduplication, and live mode lock via AsyncMock + tmp_path isolation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write test_live_submit_regression.py — 6 scenarios | bbba8ac | tests/test_live_submit_regression.py, scripts/live_submit_sop.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Order dataclass has no broker_order_id field**
- **Found during:** Task 1 — first test run
- **Issue:** `Order(broker_order_id=...)` raised `TypeError: unexpected keyword argument`. The `Order` dataclass in `adapters/base.py` does not include `broker_order_id`.
- **Fix:** Replaced `Order(...)` construction in `make_mock_adapter()` with `MagicMock()` having `broker_order_id` set as attribute.
- **Files modified:** tests/test_live_submit_regression.py
- **Commit:** bbba8ac

**2. [Rule 2 - Missing Critical Functionality] live_submit_sop.py lacked double-submit deduplication**
- **Found during:** Task 1 — Scenario 5 analysis
- **Issue:** `submit_live_order` appended to `orders_open.json` unconditionally; same `order_id` submitted twice would create two entries.
- **Fix:** Added `order_id` existence check before `orders_open.append()`; returns early with success if already present.
- **Files modified:** skills/ETF_TW/scripts/live_submit_sop.py
- **Commit:** bbba8ac

## Test Results

```
7 passed, 1 warning in 0.27s   (new file)
328 passed, 6 warnings in 4.93s  (full suite — up from 321)
```

## Scenarios Covered

| # | Scenario | Assertion |
|---|----------|-----------|
| 1 | Happy path | result.success=True, orders_open.json contains ORD001 |
| 2 | Ghost order | result.ghost=True, ghost_orders.jsonl written, orders_open NOT written |
| 3 | pre_flight_gate blocks | result.step="pre_flight_gate", adapter._submit_order_impl not called |
| 4 | Adapter exception | result.step="submit", orders_open.json not created |
| 5 | Double-submit prevention | only 1 entry for dup-001 in orders_open.json |
| 6 | Live mode locked (absent) | result.step="live_mode_gate", no broker calls |
| 6b | Live mode explicitly disabled | result.step="live_mode_gate", no broker calls |

## Security Checks

- No `instances/etf_master/state` access in test file (verified by plan constraint)
- No `api.logout()` call anywhere in test file
- All adapter calls are `AsyncMock` — no real shioaji SDK contact

## Self-Check: PASSED

- `tests/test_live_submit_regression.py` exists: FOUND
- Commit `bbba8ac` exists: FOUND
- Full suite 328 passed: CONFIRMED
