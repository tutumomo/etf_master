---
phase: 10-live-submit
plan: "02"
subsystem: [Scripts, Tests]
tags: [stress-test, ghost-order, unit-confusion, paper-mode, quality-gate]
requires: []
provides: [run_paper_stress_test, stress_test_report]
affects: [live-unlock-gate]
tech-stack:
  added: []
  patterns: [scan_fn injection for testability, atomic_save_json for report output]
key-files:
  created:
    - skills/ETF_TW/scripts/run_paper_stress_test.py
    - skills/ETF_TW/instances/etf_master/state/stress_test_report.json
  modified:
    - skills/ETF_TW/tests/test_paper_stress_test.py
key-decisions:
  - "duplicate_order_ids 跨週期追蹤為 informational only，不影響 stress_test_passed — 因為 scan_fn 每週期返回相同掛單屬正常行為，只有 ghost 和 unit confusion 是硬失敗"
requirements-completed: [QUALITY-02]
duration: "8 min"
completed: "2026-04-17"
---

# Phase 10 Plan 02: Paper Mode 壓力測試與幽靈委託偵測 Summary

Paper-mode stress test runner with ghost order detection (broker_order_id=null + verified=False) and unit confusion detection (board lot quantity not multiple of 1000) across N simulated scan cycles.

**Duration:** 8 min | **Tasks:** 2/2 | **Files:** 2 created | **Commit:** a82f0f7

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create run_paper_stress_test.py | a82f0f7 | scripts/run_paper_stress_test.py |
| 2 | Write test_paper_stress_test.py | a82f0f7 | tests/test_paper_stress_test.py |

## Deliverables

- `skills/ETF_TW/scripts/run_paper_stress_test.py` — exports `check_cycle_orders`, `run_stress_test`, `main()`
- `skills/ETF_TW/tests/test_paper_stress_test.py` — 9 pytest functions, all inline fixtures, scan_fn injection
- `skills/ETF_TW/instances/etf_master/state/stress_test_report.json` — produced at runtime

## Verification Results

1. `python scripts/run_paper_stress_test.py --cycles 5` — exits, writes stress_test_report.json (real state has unit confusion → detected correctly)
2. `cat instances/etf_master/state/stress_test_report.json` — valid JSON with all required keys
3. `.venv/bin/python3 -m pytest tests/test_paper_stress_test.py -v` — **9/9 PASS**
4. `.venv/bin/python3 -m pytest tests/ -q` — **302 passed** (>= 275 threshold)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Logic] duplicate_order_ids 不影響 stress_test_passed**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** 計畫說 "stress_test_passed = True only when ... AND no duplicates"，但 test_all_clean_cycles_pass 用相同 3 個 order_id 跑 10 cycles 並期望 PASS。若嚴格按計畫，兩個測試互相矛盾。
- **Fix:** 跨週期 duplicate_order_ids 僅作 informational 追蹤，不加入 failure_reasons。Ghost orders 和 unit confusion 才是硬失敗。
- **Files modified:** scripts/run_paper_stress_test.py
- **Commit:** a82f0f7

**Total deviations:** 1 auto-fixed (logic reconciliation). **Impact:** 符合測試規格，安全行為不變。

## Known Stubs

None — report writes real data from state files or injected scan_fn.

## Threat Flags

None.

## Self-Check: PASSED

- [x] `skills/ETF_TW/scripts/run_paper_stress_test.py` exists
- [x] `skills/ETF_TW/tests/test_paper_stress_test.py` exists
- [x] Commit a82f0f7 verified in git log
- [x] 9/9 tests pass
- [x] 302 total tests pass

## Next

Ready for 10-03 (next plan in phase 10-live-submit).
