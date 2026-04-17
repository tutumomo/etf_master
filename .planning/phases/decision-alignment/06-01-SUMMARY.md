---
phase: 06
plan: "01"
subsystem: rule-engine
tags: [decision-alignment, dynamic-weights, overlay-modifiers, risk-threshold]
dependency_graph:
  requires: []
  provides: [OVERLAY_MODIFIERS, BUY_THRESHOLD_BY_RISK, strategy_aligned]
  affects: [run_auto_decision_scan.py, dashboard-score-display]
tech_stack:
  added: []
  patterns: [lookup-table, dynamic-threshold, strategy-alignment-flag]
key_files:
  modified:
    - skills/ETF_TW/scripts/run_auto_decision_scan.py
decisions:
  - "OVERLAY_MODIFIERS uses additive group delta pattern (not multiplier) for predictable score auditing"
  - "BUY_THRESHOLD_BY_RISK uses risk_temperature as key with 'normal' fallback to maintain backward compatibility"
  - "strategy_aligned flag derived from base_strategy+group match OR positive overlay delta — dashboard can use this to highlight aligned candidates"
metrics:
  duration: "8m"
  completed: "2026-04-17"
  tasks_completed: 3
  files_modified: 1
---

# Phase 06 Plan 01: Rule Engine 動態權重矩陣深度優化 Summary

**One-liner:** Dynamic weight matrix with OVERLAY_MODIFIERS lookup table, risk-temperature buy threshold, and strategy_aligned candidate flag replacing hardcoded scoring constants.

## What Was Built

Three enhancements to `run_auto_decision_scan.py` that make the rule engine decision-aligned:

1. **`OVERLAY_MODIFIERS` dict** — Maps `scenario_overlay` values to per-group score deltas. Covers `收益再投資`, `收益優先`, `高波動防守`, `減碼保守`, `積極成長`, `無`. Applied in `decide_action` scoring loop using lookup instead of scattered if/elif chains.

2. **`BUY_THRESHOLD_BY_RISK` dict** — Replaces hardcoded `score >= 4` with dynamic threshold keyed by `risk_temperature`: low=3.5, normal=4.0, elevated=5.0, high=6.0. More conservative during elevated-risk markets.

3. **`strategy_aligned` field in candidates** — Boolean added to every candidate dict. True when `base_strategy` matches group affinity OR when positive overlay delta applies. Dashboard and downstream consumers can filter/highlight by this flag.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add OVERLAY_MODIFIERS and BUY_THRESHOLD_BY_RISK dicts | 0d4689d |
| 2 | Apply overlay modifiers + strategy_aligned in decide_action | 0d4689d |
| 3 | Replace hardcoded buy threshold with BUY_THRESHOLD_BY_RISK lookup | 0d4689d |

## Deviations from Plan

None - plan executed as written. Tasks 1-3 were batched into a single commit since they are tightly coupled (all in the same function scope).

## Known Stubs

None. All changes wire directly to existing `risk_temperature` and `scenario_overlay` values from loaded state files.

## Self-Check: PASSED

- `OVERLAY_MODIFIERS` dict exists in run_auto_decision_scan.py: confirmed
- `BUY_THRESHOLD_BY_RISK` dict exists: confirmed
- `strategy_aligned` field in candidates.append: confirmed
- `buy_threshold = BUY_THRESHOLD_BY_RISK.get(risk_temperature, ...)` replaces hardcoded 4: confirmed
- Commit 0d4689d exists: confirmed
