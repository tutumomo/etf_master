---
phase: 10-live-submit
plan: "04"
subsystem: [Scripts, Tests]
tags: [live-submit, sinopac, ordno, ghost-detection, sop]
dependency_graph:
  requires: [10-01, 10-02, 10-03]
  provides: [sinopac-ordno-fix, verify-order-landed, live-submit-sop]
  affects: [dashboard/order-submission, scripts/adapters/sinopac_adapter.py]
tech_stack:
  added: []
  patterns: [asyncio-run-in-sync-tests, lazy-import-wrapper-for-relative-modules]
key_files:
  created:
    - skills/ETF_TW/scripts/live_submit_sop.py
    - skills/ETF_TW/tests/test_sinopac_adapter_live_submit.py
  modified:
    - skills/ETF_TW/scripts/adapters/sinopac_adapter.py
decisions:
  - "用 asyncio.run() 包裝 async 測試，避免依賴 pytest-asyncio（專案未安裝）"
  - "check_order 以 thin wrapper 形式暴露在 live_submit_sop 模組層級，讓 patch('live_submit_sop.check_order') 可正常攔截"
  - "verify_order_landed 的 poll_interval_s 參數預設 1.0s，測試注入 0 以加速"
metrics:
  duration: "~15 min"
  completed: "2026-04-17"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 04: Sinopac Ordno Fix + Live Submit SOP Summary

Single-sentence: sinopac_adapter 修正 broker_order_id 讀取路徑為 `trade.order.ordno`，新增 `verify_order_landed()` 3 輪詢 ghost detection，並建立 `live_submit_sop.py` 作為唯一授權的 live 下單 SOP 入口。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix sinopac_adapter ordno + verify_order_landed | c8a9a8a | scripts/adapters/sinopac_adapter.py |
| 2 | Create live_submit_sop.py + tests | c8a9a8a | scripts/live_submit_sop.py, tests/test_sinopac_adapter_live_submit.py |

## Changes Made

### sinopac_adapter.py — ordno 修正

**舊 (bug):**
```python
order.order_id = str(getattr(trade.status, 'order_id', ''))
```

**新 (正確):**
```python
trade_order = getattr(trade, 'order', None)
order.broker_order_id = str(getattr(trade_order, 'ordno', '')) if trade_order else ''
```

### sinopac_adapter.py — verify_order_landed()

新增 async 方法，對 `list_trades()` 最多輪詢 `max_polls`（預設 3）次，間隔 `poll_interval_s`（預設 1.0s）：
- 找到 ordno → `{"verified": True, "ghost": False, "polls": N}`
- 未找到 → `{"verified": False, "ghost": True, "polls": max_polls}`
- 從不呼叫 `api.logout()`

### live_submit_sop.py — SOP 入口

完整 6 步驟管線：
1. `live_mode.json enabled=True` 檢查
2. `pre_flight_gate.check_order` (7 checks)
3. `is_confirmed=True` 人工確認
4. `adapter._submit_order_impl(order)` 送單
5. `verify_order_landed(broker_order_id)` 驗證落地
6. 落地 → 寫 `orders_open.json`；ghost → 寫 `ghost_orders.jsonl`

## Test Results

```
12 new tests: 12 passed
Full suite: 321 passed, 0 failed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Import] pre_flight_gate 相對 import 無法直接 import**
- **Found during:** Task 2
- **Issue:** `pre_flight_gate.py` 使用 `.trading_hours_gate` 相對 import，在 `live_submit_sop.py` 頂層 import 時觸發 `ImportError: attempted relative import with no known parent package`
- **Fix:** 在 `live_submit_sop.py` 建立 thin wrapper `check_order()` 函數，在函數內部做 lazy import（先嘗試 `scripts.pre_flight_gate`，fallback `pre_flight_gate`）。這讓 `patch('live_submit_sop.check_order')` 在測試中可正常攔截，生產路徑也能正確呼叫。
- **Files modified:** `scripts/live_submit_sop.py`
- **Commit:** c8a9a8a

**2. [Rule 3 - TestFramework] pytest-asyncio 未安裝**
- **Found during:** Task 1
- **Issue:** 測試用 `@pytest.mark.asyncio` 但 `pytest-asyncio` 未在 venv 中，測試全部失敗
- **Fix:** 改用 `asyncio.run()` 包裝，與專案現有 `test_trade_verification.py` 一致
- **Files modified:** `tests/test_sinopac_adapter_live_submit.py`
- **Commit:** c8a9a8a

## Threat Model Coverage

| Threat ID | Mitigation Status |
|-----------|------------------|
| T-10-04-01 (Bypass) | 實作：所有呼叫必須經過 `submit_live_order`，`is_confirmed=False` 被拒絕 |
| T-10-04-02 (Repudiation) | 實作：ghost 寫入 `ghost_orders.jsonl`，成功寫入 `orders_open.json`，皆含 ISO 時間戳 |
| T-10-04-03 (Spoofing) | 實作：`verify_order_landed` 對接 broker `list_trades()`，3 次未中即 ghost |
| T-10-04-04 (Tampering) | 實作：`atomic_save_json` (temp+rename) 防止崩潰寫入損毀 |
| T-10-04-05 (api.logout) | 確認：`sinopac_adapter.py` 無 `api.logout()` 呼叫（僅出現於 docstring 警告） |

## Self-Check: PASSED

- [x] `scripts/adapters/sinopac_adapter.py` 含 `trade.order.ordno` 提取（line 485）
- [x] `scripts/adapters/sinopac_adapter.py` 含 `verify_order_landed` 方法（line 541）
- [x] `scripts/live_submit_sop.py` 已建立
- [x] `tests/test_sinopac_adapter_live_submit.py` 已建立
- [x] commit c8a9a8a 存在
- [x] 321 passed, 0 failed
- [x] `api.logout()` 未被呼叫（僅 docstring）
