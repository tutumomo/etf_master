---
name: opencli-operate
description: Make websites accessible for AI agents. Navigate, click, type, extract, wait — using Chrome with existing login sessions. No LLM API key needed.
allowed-tools: Bash(opencli:*), Read, Edit, Write
---

# OpenCLI Operate — Browser Automation for AI Agents

Control Chrome step-by-step via CLI. Reuses existing login sessions — no passwords needed.

## Prerequisites

```bash
opencli doctor    # Verify extension + daemon connectivity
```

Requires: Chrome running + OpenCLI Browser Bridge extension installed.

## Critical Rules

1. **ALWAYS use `state` to inspect the page, NEVER use `screenshot`** — `state` returns structured DOM with `[N]` element indices, is instant and costs zero tokens. `screenshot` requires vision processing and is slow. Only use `screenshot` when the user explicitly asks to save a visual.
2. **ALWAYS use `click`/`type`/`select` for interaction, NEVER use `eval` to click or type** — `eval "el.click()"` bypasses scrollIntoView and CDP click pipeline, causing failures on off-screen elements. Use `state` to find the `[N]` index, then `click <N>`.
3. **Verify inputs with `get value`, not screenshots** — after `type`, run `get value <index>` to confirm.
4. **Run `state` after every page change** — after `open`, `click` (on links), `scroll`, always run `state` to see the new elements and their indices. Never guess indices.
5. **Chain commands aggressively with `&&`** — combine `open + state`, multiple `type` calls, and `type + getvalue` into single `&&` chains. Each tool call has overhead; chaining cuts it.
6. **`eval` is read-only** — use `eval` ONLY for data extraction (`JSON.stringify(...)`), never for clicking, typing, or navigating. Always wrap in IIFE to avoid variable conflicts: `eval "(function(){ const x = ...; return JSON.stringify(x); })()"`.
7. **Minimize total tool calls** — plan your sequence before acting. A good task completion uses 3-5 tool calls, not 15-20. Combine `open + state` as one call. Combine `type + type + click` as one call. Only run `state` separately when you need to discover new indices.
8. **Prefer `network` to discover APIs** — most sites have JSON APIs. API-based adapters are more reliable than DOM scraping.

## Command Cost Guide

| Cost | Commands | When to use |
|------|----------|-------------|
| **Free & instant** | `state`, `get *`, `eval`, `network`, `scroll`, `keys` | Default — use these |
| **Free but changes page** | `open`, `click`, `type`, `select`, `back` | Interaction — run `state` after |
| **Expensive (vision tokens)** | `screenshot` | ONLY when user needs a saved image |

## Action Chaining Rules

Commands can be chained with `&&`. The browser persists via daemon, so chaining is safe.

```bash
# GOOD: open + inspect in one call
opencli operate open https://example.com && opencli operate state

# GOOD: fill form in one call
opencli operate type 3 "hello" && opencli operate type 4 "world" && opencli operate click 7

# GOOD: type + verify
opencli operate type 5 "test@example.com" && opencli operate get value 5

# GOOD: click + wait + state
opencli operate click 12 && opencli operate wait time 1 && opencli operate state
```

Page-changing commands (`open`, `back`, `click` on links) should go LAST in a chain.

## Core Workflow

1. **Navigate**: `opencli operate open <url>`
2. **Inspect**: `opencli operate state` → elements with `[N]` indices
3. **Interact**: use indices — `click`, `type`, `select`, `keys`
4. **Wait** (if needed): `opencli operate wait selector ".loaded"` or `wait text "Success"`
5. **Verify**: `opencli operate state` or `opencli operate get value <N>`
6. **Extract**: `opencli operate eval "JSON.stringify(...)"`
7. **Close**: `opencli operate close`

## Commands

### Navigation
```bash
opencli operate open <url>              # Open URL (page-changing)
opencli operate back                    # Go back (page-changing)
opencli operate scroll down             # Scroll (up/down, --amount N)
```

### Inspect (free & instant)
```bash
opencli operate state                   # Structured DOM with [N] indices — PRIMARY tool
opencli operate screenshot [path.png]   # Save visual to file — ONLY for user deliverables
```

### Get (free & instant)
```bash
opencli operate get title               # Page title
opencli operate get url                 # Current URL
opencli operate get text <index>        # Element text content
opencli operate get value <index>       # Input value (verify after type)
opencli operate get html                # Full page HTML
opencli operate get attributes <index>  # Element attributes
```

### Interact
```bash
opencli operate click <index>           # Click element [N]
opencli operate type <index> "text"     # Type into element [N]
opencli operate select <index> "option" # Select dropdown
opencli operate keys "Enter"            # Press key (Enter, Escape, Tab)
```

### Wait
```bash
opencli operate wait time 3             # Wait N seconds
opencli operate wait selector ".loaded" # Wait until element appears
opencli operate wait text "Success"     # Wait until text appears
```

### Extract (read-only)
```bash
opencli operate eval "document.title"
opencli operate eval "JSON.stringify([...document.querySelectorAll('h2')].map(e => e.textContent))"
# Wrap complex logic in IIFE:
opencli operate eval "(function(){ const items = [...document.querySelectorAll('.item')]; return JSON.stringify(items.map(e => e.textContent)); })()"
```

### Network (API Discovery)
```bash
opencli operate network                  # Show captured API requests
opencli operate network --detail 3       # Full response body of request #3
opencli operate network --all           # Include static resources
```

### Sedimentation (Save as CLI)
```bash
opencli operate init hn/top             # Generate adapter scaffold
opencli operate verify hn/top           # Test the adapter
```

### Session
```bash
opencli operate close                   # Close automation window
```

## Strategy Guide

| Strategy | When | browser: |
|----------|------|----------|
| `Strategy.PUBLIC` | Public API, no auth | `false` |
| `Strategy.COOKIE` | Needs login cookies | `true` |
| `Strategy.UI` | Direct DOM interaction | `true` |

**Always prefer API over UI** — if you discovered an API during browsing, use `fetch()` directly.

## Common Pitfalls

1. **`form.submit()` fails in automation** — Navigate directly to the URL instead
2. **SPA pages need `wait` before extraction** — Always `wait selector` or `wait text` before `eval`
3. **Use `state` before clicking** — Never guess indices from memory
4. **`evaluate` runs in browser context** — Node.js APIs (`fs`, `path`) are NOT available
5. **Backticks in `page.evaluate` break JSON storage** — Use function-style evaluate instead