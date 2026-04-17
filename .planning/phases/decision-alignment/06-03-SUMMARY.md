---
phase: "06"
plan: "03"
subsystem: decision-alignment
tags: [consensus, strategy-alignment, wiki-injection, confidence-adjustment]
dependency_graph:
  requires: [06-01-PLAN, 06-02-PLAN]
  provides: [strategy-weighted-consensus, wiki-background-injection]
  affects: [run_auto_decision_scan.py, generate_ai_agent_response.py]
tech_stack:
  added: []
  patterns: [helper-function-extraction, graceful-fallback, backward-compatible-defaults]
key_files:
  modified:
    - skills/ETF_TW/scripts/run_auto_decision_scan.py
    - skills/ETF_TW/scripts/generate_ai_agent_response.py
decisions:
  - _adjust_confidence() extracted as standalone helper before resolve_consensus() for testability
  - wiki_note injected into candidate reason string rather than a separate field, keeping payload schema stable
  - WIKI_DIR scoped inside _build_agent_reasoning() to avoid module-level path side effects
metrics:
  duration: "~8 minutes"
  completed: "2026-04-17T02:14:48Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 06 Plan 03: 共識仲裁策略對齊加權 + Wiki 背景注入 Summary

## One-liner

Strategy-aligned confidence adjustment in resolve_consensus() via _adjust_confidence() helper, plus graceful llm-wiki ETF page injection into AI agent candidate reasoning.

## What Was Built

### Task 1: resolve_consensus() Strategy Alignment Upgrade

Added `_adjust_confidence()` helper and upgraded `resolve_consensus()` in `run_auto_decision_scan.py`:

- New optional params: `rule_strategy_aligned: bool | None = None`, `ai_strategy_aligned: bool | None = None`
- `_adjust_confidence(base, rule_aligned, ai_aligned)` logic:
  - both True + base=='medium' → 'high'
  - either False + base=='high' → 'medium'
  - either False + base=='medium' → 'low'
  - otherwise → unchanged
- `strategy_alignment_signal: {'rule': ..., 'ai': ...}` added to all Tier 1/2/3 return dicts
- All existing callers without new params continue to work (None defaults = no adjustment)

### Task 2: llm-wiki ETF Background Injection

Added wiki background loading in `_build_agent_reasoning()` in `generate_ai_agent_response.py`:

- `WIKI_DIR = ROOT / 'instances' / 'etf_master' / 'llm-wiki' / 'etf'`
- Iterates top 3 scored candidates, tries to load `{sym}.md` from WIKI_DIR
- Reads up to 800 chars, extracts first `## ` section header as `wiki_note`
- `wiki_note` appended to `candidate['reason']` string if wiki page exists
- Full try/except protection — zero impact if wiki dir or pages absent

## Verification Results

```
grep "strategy_alignment_signal" run_auto_decision_scan.py  → 8 occurrences
grep "WIKI_DIR" generate_ai_agent_response.py               → 1 occurrence
.venv/bin/python -c "import generate_ai_agent_response; print('OK')"  → OK
pytest -k "consensus or ai_decision" (21 passed, 1 pre-existing UI test fail)
```

The 1 failing test (`test_ai_decision_bridge_actions.py::test_overview_template_contains_ai_bridge_action_buttons`) checks for `refreshAIDecisionBackground()` in the dashboard template — this is pre-existing and unrelated to this plan's changes.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Wiki injection gracefully no-ops when wiki pages don't exist; no stub data flows to UI.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundary changes introduced.

## Self-Check: PASSED

- `skills/ETF_TW/scripts/run_auto_decision_scan.py` — FOUND, contains `strategy_alignment_signal` and `_adjust_confidence`
- `skills/ETF_TW/scripts/generate_ai_agent_response.py` — FOUND, contains `WIKI_DIR` and `wiki_note`
- Commit `362643d` (Task 1) — FOUND
- Commit `40364db` (Task 2) — FOUND
