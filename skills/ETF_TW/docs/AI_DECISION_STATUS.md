# AI Decision Status (Hermes Handoff)

> Purpose: provide a single handoff index for the AI decision mainline in the Hermes-hosted ETF_TW skill.

## Current status

### Completed
- P1: Layered review cron landing was historically verified during the legacy migration phase.
- P2: Agent-facing docs surfaced in `README.md` pointing to cron standards and registration entry.
- P3: Quality-state layer materialized: `ai_decision_quality.json` contains numeric review quality fields and is refreshed via `auto_quality_refresh.py`.

### In progress / remaining
- P4: Continue replacing legacy cron assumptions with Hermes-native scheduling / verification flow.

## Canonical docs to read first
- `docs/AI_RESEARCH_METHOD.md`
- `docs/LAYERED_REVIEW_SCHEDULING.md`
- `docs/LAYERED_REVIEW_CRON_STANDARD.md`
- `docs/STATE_ARCHITECTURE.md`

## Canonical state rules
- Canonical runtime truth: `instances/<agent_id>/state/`
- Root `state/` is shared-only and must not contain positions / orders / portfolio snapshots.

## Canonical scripts
### Layered review
- Plan: `scripts/write_layered_review_plan.py`
- Register: `scripts/register_layered_review_jobs.py`
- Runtime runner: `scripts/auto_post_review_cycle.py`

### Quality state
- Compute: `scripts/score_decision_quality.py`
- Refresh: `scripts/auto_quality_refresh.py`
- State writer: `scripts/ai_decision_quality_state.py`

## Notes / pitfalls
- If you see mismatched holdings between dashboard and an agent reply, suspect root-vs-instance state drift first.
- Do not trust local registry alone for cron landing verification.
