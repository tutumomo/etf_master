---
name: hermes-config-proof-first
description: Proof-first workflow for reviewing and changing Hermes settings without guessing. Ensures active profile verification, doc-grounded recommendations, and post-change validation.
version: 1.0.1
---

# Hermes config proof-first workflow

Use this when a user asks to review or modify Hermes settings and explicitly wants non-hallucinated answers.

## Trigger conditions
- User says "不要靠幻覺/不要用猜的" or equivalent
- User asks "哪個設定要調" / "review config"
- Multiple profiles may exist (`default` and named profiles)

## Steps
1. Confirm active config target
   - `echo $HERMES_HOME`
   - `hermes config path`
   - `hermes profile list`

2. Capture current runtime state
   - `hermes config check`
   - `hermes tools list`

3. Ground recommendations in official docs
   - Prefer local docs under `website/docs/*.md` when available
   - If web docs are rendered HTML, use GitHub raw markdown for reliable parsing
   - Extract exact lines for any recommendation

4. Check secret prerequisites safely
   - Verify required `.env` keys as `SET/MISSING` only
   - Never print secret values

5. Produce prioritized changes
   - P0: removes friction while keeping safeguards
   - P1: reliability/resilience
   - P2: optional optimization

6. If applying changes
   - Run `hermes config set ...`
   - Re-run `hermes config check`
   - Re-run `hermes tools list`
   - Restart gateway if needed

## Pitfalls
- Don’t assume default profile is active
- Don’t claim a feature is enabled solely from memory
- Don’t paste secret values from `.env`

## Output format (recommended)
- Active config path
- Doc evidence (file + line or URL + snippet)
- Recommended changes by priority (P0/P1/P2)
- Exact commands to apply and verify
