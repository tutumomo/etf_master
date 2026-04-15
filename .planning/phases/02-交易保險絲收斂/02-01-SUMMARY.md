# Phase 2 Plan 1: Sizing Engine and Pre-flight Gate Summary

## Objective
實作 sizing_engine_v1 與統一的 pre-flight gate，確保交易路徑遵循相同的風險控制邏輯。

## Key Changes
- **Sizing Engine (v1)**: 根據現金、集中度上限、單筆上限和風險溫度計算建議股數。
- **Pre-flight Gate**: 整合風控邏輯，統一買賣雙向檢核。
- **Unified Tests**: 建立 9 個單元測試涵蓋超限、超庫存、非法價格/數量、非交易時段等情境。

## Key Files Created
- `skills/ETF_TW/scripts/sizing_engine_v1.py`
- `skills/ETF_TW/scripts/pre_flight_gate.py`
- `skills/ETF_TW/tests/test_sizing_v1.py`
- `skills/ETF_TW/tests/test_fuse_v1.py`

## Verification Results
- `pytest skills/ETF_TW/tests/test_sizing_v1.py`: PASSED (via unittest)
- `pytest skills/ETF_TW/tests/test_fuse_v1.py`: PASSED (9/9 cases)

## Deviations from Plan
- None.

## Self-Check: PASSED
- [x] Sizing engine correctly calculates quantity.
- [x] Pre-flight gate blocks invalid orders.
- [x] Unit tests pass for all core fuse logic.
