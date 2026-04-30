# Dirty State Audit — 2026-04-30

## Scope

This audit was started after release `v1.8.2` to separate project-relevant changes from Hermes profile runtime noise before continuing broker reconciliation work.

## Findings

### 1. `.gitignore` was structurally broken

The tracked `.gitignore` contained literal `\n` text in several lines. Many ignore rules were therefore ineffective, causing runtime directories, checkpoints, cron outputs, caches, auth files, disabled skills, and temporary files to flood `git status`.

Action taken:
- Rewrote `.gitignore` into normal newline-delimited rules.
- Kept the original intent: ignore runtime/tool state while keeping ETF_TW, taiwan-finance, graphify, and absorbed finance references visible.
- Added explicit ignores for high-volume local-only state: `checkpoints/`, `cron/output/`, `graphify-out/cache/`, `instances/`, `state-snapshots/`, `_disabled/`, `pastes/`, `platforms/pairing/`, and `tmp_*.py`.

Verification:
- `git check-ignore` now matches representative runtime files such as `.env`, `cron/output/...`, `checkpoints/...`, non-finance skills, and `graphify-out/cache/...`.
- Untracked candidates dropped from thousands of files to a small review set.

### 2. Remaining untracked candidates need explicit decision

Keep for review:
- `docs/superpowers/plans/2026-04-22-sensor-degradation.md`
- `docs/superpowers/plans/2026-04-22-learned-rules-evolution.md`
- `scripts/sync_worldmonitor_daily.py`
- `scripts/sync_worldmonitor_watch.py`
- `skills/taiwan-finance/references/stock-analysis-tw.md`
- `skills/taiwan-finance/references/stock-market-pro-tw.md`
- `skins/etf-master.yaml`
- `GEMINI.md`

Recommended handling:
- Track the two `taiwan-finance` references if the absorbed stock-analysis / stock-market-pro knowledge is intended to survive clone.
- Track the two `worldmonitor` wrappers only if cron or Hermes automation uses root-level wrapper scripts.
- Review the two superpowers plans before implementing; they are project-relevant but not active code.
- Treat `GEMINI.md` and `skins/etf-master.yaml` as local/tooling candidates unless the project wants cross-agent onboarding and shared skin configuration.

### 3. Remaining tracked dirty files are mixed-risk

Tracked local/runtime state still dirty:
- `.claude/settings.local.json`
- `.hermes_history`
- `.skills_prompt_snapshot.json`
- `.update_check`
- `channel_directory.json`
- `config.yaml`
- `cron/jobs.json`
- `memories/USER.md`
- `models_dev_cache.json`
- `skills/.bundled_manifest`

Recommended handling:
- Do not commit these as-is.
- If they should become local-only, remove them from git tracking in a dedicated cleanup commit after confirming clone expectations.
- `cron/jobs.json` contains only scheduler runtime timestamps/counts since `v1.8.2`; avoid committing those runtime-only deltas.

### 4. Absorbed skill deletions are still visible

Tracked deletions remain for:
- `skills/stock-analysis-tw/**`
- `skills/stock-market-pro-tw/**`
- `skills/graphify`

Context:
- `v1.8.2` already removed live cron dependency on `stock-analysis-tw` / `stock-market-pro-tw`.
- Absorbed knowledge references now exist under `skills/taiwan-finance/references/`.

Recommended handling:
- Decide whether to keep these skills deleted as a formal repository cleanup, or restore the tracked copies and rely on cron no longer calling them.
- Do not mix this repository-shape decision with broker reconciliation code.

### 5. Wiki entity snapshots are generated market data

Modified files:
- `wiki/entities/0050-yuanta-taiwan-50.md`
- `wiki/entities/0056-yuanta-high-dividend.md`
- `wiki/entities/006208-fubon-taiwan-50.md`
- `wiki/entities/00679B-yuanta-us-20y-bond.md`
- `wiki/entities/00687B-cathay-20y-us-bond.md`
- `wiki/entities/00713-yuanta-high-div-low-vol.md`
- `wiki/entities/00830-cathay-philly-semiconductor.md`
- `wiki/entities/00878-cathay-esg-high-dividend.md`
- `wiki/entities/00919-capital-taiwan-selected-high-dividend.md`
- `wiki/entities/00922-zhaoying-blue-chip-30.md`
- `wiki/entities/00929-fuhwa-tech-optimal-income.md`

Recommended handling:
- Commit these only when intentionally syncing latest wiki market snapshots.
- Otherwise leave them out of functional commits.

## Next Recommended Step

Proceed to broker reconciliation close-the-loop only after keeping this audit boundary:
- Code/docs for reconciliation may be edited.
- Runtime state and scheduler timestamp deltas should remain unstaged.
- Repository-shape cleanup for absorbed skills should be a separate decision.
