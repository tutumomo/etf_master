# Path Inventory (PATH-02)

This document maps the active project files to their legacy counterparts and establishes the project's modification policy.

## Active vs Legacy Mapping

| Category | Active Path (Hermes) | Legacy Path (OpenClaw) | Status |
|----------|----------------------|-------------------------|--------|
| Skill Root | `~/.hermes/profiles/etf_master/skills/ETF_TW` | `~/.openclaw/skills/ETF_TW` | **Active** |
| Scripts | `.../skills/ETF_TW/scripts/` | `~/.openclaw/skills/ETF_TW/scripts/` | **Active** |
| Data | `.../skills/ETF_TW/data/` | `~/.openclaw/skills/ETF_TW/data/` | **Active** |
| State | `.../skills/ETF_TW/state/` | `~/.openclaw/skills/ETF_TW/state/` | **Active** |
| Config | `~/.hermes/profiles/etf_master/config.yaml` | `~/.openclaw/config.yaml` | **Active** |

## Modification Policy

**All future project modifications must only modify active paths (under `~/.hermes/...`).**

- Do **not** modify files in legacy paths (`~/.openclaw/...`) unless specifically performing a one-time migration.
- Always ensure you are working within the `etf_master` profile.
- If a script needs to be updated, update it in the active path and verify it works before considering the task complete.

---
*Freeze Statement:* This project is now frozen in legacy paths. Development continues exclusively in the Hermes profile.
