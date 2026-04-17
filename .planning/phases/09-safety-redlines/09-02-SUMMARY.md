---
phase: "09"
plan: "02"
subsystem: Dashboard
tags: [dashboard, safety-redlines, api, tooltip, settings-ui]
dependency_graph:
  requires: [09-01]
  provides: [redline-read-api, redline-write-api, dashboard-redline-card]
  affects: [dashboard/app.py, dashboard/templates/overview.html]
tech_stack:
  added: [FastAPI-endpoints, form-driven-settings-ui]
  patterns: [server-side-validation, banner-feedback]
key_files:
  modified:
    - skills/ETF_TW/dashboard/app.py
    - skills/ETF_TW/dashboard/templates/overview.html
decisions:
  - the dashboard reads and writes the same instance-scoped safety_redlines.json used by the gate
  - AI confidence threshold is translated into a human-readable level for UI clarity
  - the redline editor lives as a dedicated full-width card rather than being buried inside strategy controls
metrics:
  completed: "Historical implementation with later dashboard fixes preserved in current tree"
  tasks_completed: 3
  files_changed: 2
---

# Phase 09 Plan 02: Dashboard Safety Redlines UI Summary

## One-liner

Added a dedicated dashboard card for editing Safety Redlines, backed by read/write APIs that persist settings to the same state file used by the trading gate.

## What Was Built

### Task 1: Safety Redlines API

`skills/ETF_TW/dashboard/app.py` now exposes:

- `GET /api/safety-redlines`
- `POST /api/safety-redlines/update`

The update path validates the payload and persists back to `safety_redlines.json`, keeping UI edits and backend enforcement aligned.

### Task 2: Dashboard Redline Management Card

`skills/ETF_TW/dashboard/templates/overview.html` now includes:

- Full-width `Safety Redlines` card.
- Editable fields for amount cap, cash percentage cap, share cap, concentration cap, daily loss breaker, and AI confidence threshold.
- Inline banner feedback after save.
- Tooltip copy for operator-facing explanation.
- `saveSafetyRedlines()` client-side handler to call the update API.

### Task 3: Later UI Hardening

The dashboard card was subsequently stabilized by follow-up dashboard fixes in the current repo history, including test-driven corrections to banner behavior and surrounding control-panel interactions.

## Verification Results

Current codebase evidence:

```text
app.py contains get_safety_redlines_api() and update_safety_redlines_api()
overview.html contains card_safety_redlines, six editable fields, enabled toggle, and saveSafetyRedlines()
```

## Deviations from Plan

- The surviving repo history shows the end state plus later hardening, not the original one-shot implementation commit before ETF_TW was imported into this repo.
- The dashboard implementation includes an additional `enabled` toggle and human-readable `ai_confidence_level`, which are consistent extensions beyond the original minimum plan.

## Traceability

- Imported implementation snapshot: `41c65a9`
- Dashboard regression fix validating the section and banner: `233a3d8`
- Related control-panel stabilization in the same area: `69700df`

## Self-Check: PASSED

- [x] Dashboard exposes read/write Safety Redlines API routes
- [x] Overview template contains a dedicated Safety Redlines card
- [x] Editable UI fields cover all core thresholds
- [x] Save flow is wired to persistent state
