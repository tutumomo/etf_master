---
phase: "08"
plan: "03"
subsystem: Dashboard
tags: [strategy-update, full-pipeline, reactive-ui]
dependency_graph:
  requires: [08-01, 08-02]
  provides: [strategy-update-full-pipeline-linkage]
  affects: [skills/ETF_TW/dashboard/app.py]
tech_stack:
  added: []
  patterns: [helper-reuse, background-trigger-linkage]
key_files:
  modified:
    - skills/ETF_TW/dashboard/app.py
decisions:
  - strategy changes should trigger the same full-pipeline helper used elsewhere instead of a lighter rescan path
  - pipeline execution stays behind helper indirection to keep UI-triggered actions consistent
metrics:
  completed: "Historical implementation preserved in imported dashboard snapshot"
  tasks_completed: 2
  files_changed: 1
---

# Phase 08 Plan 03: Strategy Update to Full Pipeline Linkage Summary

## One-liner

Updated dashboard strategy changes to flow through `_run_full_pipeline_helper()` so a strategy switch triggers the full sync and analysis chain instead of a narrower rescan path.

## What Was Built

In `skills/ETF_TW/dashboard/app.py`, the strategy update flow now calls `_run_full_pipeline_helper()` from the strategy update endpoints, linking operator strategy changes to the same full pipeline execution path used by the streamlined dashboard actions.

## Verification Results

Current codebase evidence:

```text
strategy_update(...) calls _run_full_pipeline_helper()
_run_full_pipeline_helper() is defined and reused by the dashboard API layer
```

## Deviations from Plan

- The original standalone implementation commit predates the ETF_TW inline import and is not isolated in the current history.
- The current `app.py` shows multiple call sites using `_run_full_pipeline_helper()`, which is a stronger end state than the original single-linkage requirement.

## Traceability

- Imported dashboard snapshot: `41c65a9`
- Current dashboard lineage continues through later control-panel work such as `7a608f5`

## Self-Check: PASSED

- [x] `strategy_update` path is linked to `_run_full_pipeline_helper()`
- [x] Phase 08 no longer has a missing summary artifact for plan 03
