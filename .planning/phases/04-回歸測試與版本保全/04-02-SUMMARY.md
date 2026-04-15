---
phase: 04-回歸測試與版本保全
plan: 02
subsystem: ETF_TW/tests
tags: [regression-testing, ui-flow, sizing-policy]
dependency_graph:
  requires: [04-01-PLAN.md]
  provides: [UI Flow State Enforcement Test, Sizing Policy Dynamic Load Test]
  affects: [pre_flight_gate.py]
tech_stack:
  added: [pytest]
  patterns: [TDD, Regression Test]
key_files:
  created: [skills/ETF_TW/tests/test_ui_flow.py, skills/ETF_TW/tests/test_sizing_policy.py]
  modified: [skills/ETF_TW/scripts/pre_flight_gate.py]
key_decisions:
  - 確保 preview/confirm/submit 的連續性狀態防堵在 `pre_flight_gate.py` 中正確實作並撰寫測試。
  - 將 Sizing Policy 變更的即時反映納入回歸測試，確認計算引擎符合新的閾值。
metrics:
  duration_minutes: 5
  completed_date: "2026-04-16"
---

# Phase 04 Plan 02: 建立回歸測試與狀態強制鎖定 (UI Flow & Sizing Policy) Summary

建立並通過了針對持倉票據狀態流轉與 Sizing Policy 變更的回歸測試。

## Done Tasks
- **Task 1: 建立持倉票據狀態流轉回歸測試 (TEST-04)**
  - 實作了 `test_ui_flow.py`，測試 `pre_flight_gate.py` 的狀態防堵。
  - 驗證直接送出未經 `confirm` 的訂單將會被攔截 (`missing_confirm_flag`)。
  - commit: `71fdd55`
- **Task 2: 建立 Sizing 政策變更生效回歸測試 (TEST-05)**
  - 實作了 `test_sizing_policy.py`，動態測試不同現金比例上限。
  - 確認政策變更後可以無縫且即時地反映在 `exceeds_sizing_limit` 與 `allowed` 張數的結果中。
  - commit: `71fdd55`

## Deviations from Plan
None - plan executed exactly as written.

## Threat Flags
None.
