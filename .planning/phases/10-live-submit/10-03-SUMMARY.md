---
phase: 10-live-submit
plan: "03"
subsystem: [Scripts, Tests]
tags: [backtest, quality-gate, ai-decision, pnl, metrics]
dependency_graph:
  requires: []
  provides: [backtest_results.json, backtest_decision_outcomes.py]
  affects: [10-05-live-unlock-gate]
tech_stack:
  added: []
  patterns: [price_fetcher injection, yfinance multi-index handling, equity curve drawdown]
key_files:
  created:
    - skills/ETF_TW/scripts/backtest_decision_outcomes.py
    - skills/ETF_TW/tests/test_backtest_decision_outcomes.py
  modified: []
decisions:
  - "price_fetcher 注入模式確保測試完全隔離，不需 unittest.mock.patch"
  - "yfinance 新版 multi-index DataFrame 用 squeeze() 後再取 float 處理"
  - "max_drawdown 以 equity curve peak-to-trough 計算，非單筆最大虧損"
metrics:
  duration: "249s"
  completed: "2026-04-17T07:17:23Z"
  tasks_completed: 2
  files_changed: 2
---

# Phase 10 Plan 03: Backtest Decision Outcomes Summary

AI 決策歷史回測引擎，讀取 `ai_decision_outcome.jsonl`，計算 PnL、勝率、最大回撤、夏普比率，並以 `quality_gate_passed` 欄位輸出 `backtest_results.json` 供 10-05 live 解鎖閘門消費。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests | 1babd7c | tests/test_backtest_decision_outcomes.py |
| 2 (GREEN) | backtest_decision_outcomes.py | e7da08e | scripts/backtest_decision_outcomes.py |

## Verification Results

1. `backtest_decision_outcomes.py` 執行成功，退出碼 0，寫入 `backtest_results.json`
2. `quality_gate_passed: True`（基於 5 筆歷史決策，win_rate=1.0, max_drawdown=0.0）
3. 10 個 unit tests 全部通過（無真實 yfinance 呼叫）
4. 完整測試套件：301 passed（超過 275 門檻）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] yfinance multi-index DataFrame float() 轉換失敗**
- **Found during:** Task 2 GREEN 驗證（CLI 執行）
- **Issue:** yfinance 新版回傳 `df["Close"]` 為 multi-index DataFrame，直接 `float(df["Close"].iloc[0])` 拋 `TypeError: float() argument must be a string or a real number, not 'Series'`
- **Fix:** 加入 `.squeeze()` 轉換後再 try/except 轉 float，若仍為 Series 再取 `.iloc[0]`
- **Files modified:** `scripts/backtest_decision_outcomes.py`
- **Commit:** e7da08e

**2. [Rule 1 - Bug] `atomic_save_json` / `safe_load_jsonl` 接受 Path 非 str**
- **Found during:** 首次 CLI 執行
- **Issue:** `safe_load_jsonl(str(path))` 拋 `AttributeError: 'str' object has no attribute 'exists'`
- **Fix:** 移除 `str()` 包裝，直接傳 `Path` 物件
- **Commit:** e7da08e

## Self-Check: PASSED

- FOUND: skills/ETF_TW/scripts/backtest_decision_outcomes.py
- FOUND: skills/ETF_TW/tests/test_backtest_decision_outcomes.py
- FOUND commit: 1babd7c (RED)
- FOUND commit: e7da08e (GREEN)
