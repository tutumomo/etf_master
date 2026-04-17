---
phase: 10-live-submit
plan: "05"
subsystem: [Dashboard, Tests]
tags: [live-gate, double-confirm, quality-gate, xss-prevention, LIVE-02]
dependency_graph:
  requires: [10-01, 10-02, 10-03]
  provides: [live_mode.json written by dashboard unlock, /api/live-mode/status, /api/live-mode/unlock]
  affects: [live_submit_sop.py (10-04 reads live_mode.json)]
tech_stack:
  added: [LiveUnlockRequest Pydantic model, zoneinfo.ZoneInfo for Asia/Taipei timestamps]
  patterns: [TDD RED/GREEN, server-side double-confirm enforcement, quality gate re-check on every POST]
key_files:
  created:
    - skills/ETF_TW/tests/test_live_mode_gate.py
  modified:
    - skills/ETF_TW/dashboard/app.py
    - skills/ETF_TW/dashboard/templates/overview.html
decisions:
  - "Server-side double-confirm enforced on every POST (not just UI disabled state) per T-10-05-01"
  - "Quality gate re-checked on every unlock request to prevent stale state bypass"
  - "All JS DOM updates use textContent to prevent XSS from API response data (T-10-05-05)"
  - "Unlock button disabled in HTML when quality_gate_passed=false (defense-in-depth)"
  - "Idempotent unlock: second call with correct inputs also returns 200"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-17T07:25:02Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 05: Live 模式授權閘門 Dashboard UI 與雙重確認 Summary

**One-liner:** FastAPI Live 模式授權閘門，雙重確認字串 + 品質閘門伺服器端強制驗證，含 overview.html 卡片 UI 與 7 個合約測試。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | TDD 失敗測試（7個） | 5a2edf6 | tests/test_live_mode_gate.py |
| GREEN | 端點實作 + UI 卡片 | 7a608f5 | dashboard/app.py, overview.html, tests/ |

## What Was Built

### /api/live-mode/status (GET)
- 回傳 `enabled`, `quality_gate_passed`, `unlocked_at`, `backtest_summary`
- 當 `live_mode.json` 不存在時回傳 `enabled: false`
- 當 `backtest_results.json` 不存在時回傳 `quality_gate_passed: false`

### /api/live-mode/unlock (POST)
- 接受 `LiveUnlockRequest(confirm_1, confirm_2)`
- confirm_1 != "ENABLE LIVE TRADING" 或 confirm_2 != "I UNDERSTAND REAL MONEY IS AT RISK" → 400
- quality_gate_passed=false → 403
- 成功時寫入 `live_mode.json` (atomic_save_json)，含 `unlocked_at` 時戳與 `unlocked_by: "dashboard"`
- 冪等：第二次呼叫也回傳 200

### Live 模式授權閘門 UI 卡片 (overview.html)
- 紅框卡片，顯示目前模式、品質閘門狀態、回測摘要
- 品質閘門未通過時：解鎖按鈕 `disabled` + 顯示說明文字
- 品質閘門通過時：顯示解鎖表單，按鈕啟用
- 所有 JS DOM 更新使用 `textContent`，無任何 `innerHTML` 插入 API 資料

## Security Compliance (Threat Model)

| Threat ID | Status |
|-----------|--------|
| T-10-05-01 Elevation of Privilege | Mitigated — 雙重確認伺服器端強制 + 每次 POST 重新檢查品質閘門 |
| T-10-05-02 Spoofing (unauthenticated) | Accepted — localhost-only；未來可加 HTTPS/auth (注記在程式碼中) |
| T-10-05-03 Tampering live_mode.json | Mitigated — atomic_save_json 防止部分寫入 |
| T-10-05-04 Repudiation | Mitigated — unlocked_at + unlocked_by 稽核時戳 |
| T-10-05-05 XSS | Mitigated — 所有 API 資料僅以 textContent 渲染 |

## Test Results

```
tests/test_live_mode_gate.py — 7/7 passed
Full suite: 316 passed, 5 pre-existing failures (test_sinopac_adapter_live_submit.py)
Requirement: >= 302 passed — SATISFIED
```

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing issues discovered (out of scope, logged to deferred-items.md):
- `subprocess.Popen(shell=True)` at app.py lines 1197, 1238 — pre-existing, not introduced by this plan
- 5 pre-existing test failures in test_sinopac_adapter_live_submit.py

## Self-Check: PASSED

- [x] `skills/ETF_TW/dashboard/app.py` — contains `/api/live-mode/status` and `/api/live-mode/unlock`
- [x] `skills/ETF_TW/dashboard/templates/overview.html` — contains `live-mode-gate`
- [x] `skills/ETF_TW/tests/test_live_mode_gate.py` — 7/7 tests pass
- [x] Commits: 5a2edf6 (RED), 7a608f5 (GREEN/feat)
- [x] No innerHTML with API data in new card block
- [x] Unlock button disabled in HTML when quality gate not passed
