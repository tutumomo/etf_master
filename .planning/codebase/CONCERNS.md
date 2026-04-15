# Codebase Concerns

**Analysis Date:** 2026-04-15

## Tech Debt

### God File: `etf_tw.py` (1203 lines)
- Issue: Single CLI entry point handles 20+ subcommands with all logic inline. No separation between CLI parsing, business logic, and I/O.
- Files: `skills/ETF_TW/scripts/etf_tw.py`
- Impact: Any change to one command risks breaking others. Hard to test individual commands in isolation. The `main()` function is a 70-line if/elif chain (lines 1127-1199) dispatching commands.
- Fix approach: Extract each `cmd_*` function into its own module under `scripts/commands/`. Keep `etf_tw.py` as thin dispatcher only.

### Duplicate Adapter: `sinopac_adapter.py` vs `sinopac_adapter_enhanced.py`
- Issue: Two SinoPac adapters exist with overlapping functionality. The "enhanced" version has unimplemented method stubs for critical operations.
- Files: `skills/ETF_TW/scripts/adapters/sinopac_adapter.py` (573 lines), `skills/ETF_TW/scripts/adapters/sinopac_adapter_enhanced.py` (374 lines)
- Impact: The enhanced adapter returns `None` for `get_order_status()` (line 363) and `False` for `cancel_order()` (line 368) with `# TODO` comments. If code ever routes to the enhanced adapter, orders cannot be queried or cancelled.
- Fix approach: Merge the enhanced adapter's callback/limit-check features into the base adapter, then delete the enhanced version. Update `base.py:get_adapter()` to use a single sinopac adapter.

### Proliferated `sys.path` Manipulation
- Issue: Nearly every script manually calls `sys.path.append(str(ROOT))` and/or `sys.path.append(str(ROOT / 'scripts'))` at the top. Over 30 scripts do this, with inconsistent patterns (some use `insert(0,...)`, some use `append`).
- Files: `skills/ETF_TW/scripts/generate_ai_decision_response.py` (lines 9-10), `skills/ETF_TW/scripts/ai_reflection_lifecycle.py` (lines 11-12), `skills/ETF_TW/scripts/update_decision_outcomes.py` (lines 13-14), and many more
- Impact: Import resolution order changes depending on which `sys.path` entry wins. Can cause subtle bugs where the wrong module is imported. Makes scripts fragile when invoked from different working directories.
- Fix approach: Add a single `conftest`-style bootstrap at the package level, or install ETF_TW as an editable package so Python resolves imports naturally.

### Hardcoded Profile Paths
- Issue: Several scripts hardcode `~/.hermes/profiles/etf_master/skills/ETF_TW/` instead of using `context.get_instance_dir()` or `Path(__file__).resolve().parents[N]`.
- Files: `skills/ETF_TW/scripts/sync_news_from_rss.py` (line 13), `skills/ETF_TW/scripts/sync_shioaji_data.py` (lines 8, 13), `skills/ETF_TW/scripts/diag_shioaji_vix.py` (line 7), `skills/ETF_TW/scripts/diag_shioaji_contracts.py` (line 7), `skills/ETF_TW/scripts/backfill_outcomes.py` (line 35), `skills/ETF_TW/scripts/register_standard_cron_pack.py` (line 74)
- Impact: Breaks multi-profile support. If a second Hermes profile is created, these scripts still read/write to the `etf_master` profile.
- Fix approach: Replace all hardcoded paths with `Path(__file__).resolve().parents[N]` pattern or call `context.get_instance_dir()` / `context.get_state_dir()`.

### Bare `except:` Clauses (Silent Failure)
- Issue: Multiple locations use bare `except:` (no exception type specified), silently swallowing all errors including `KeyboardInterrupt` and `SystemExit`.
- Files: `skills/ETF_TW/scripts/etf_tw.py` (lines 621, 654, 779), `skills/ETF_TW/scripts/dashboard_guard.py` (line 48), `skills/ETF_TW/scripts/generate_intraday_tape_context.py` (line 27), `skills/ETF_TW/scripts/etf_core/context.py` (line 95), `skills/ETF_TW/scripts/refresh_monitoring_state.py` (line 90)
- Impact: Configuration loading errors are silently ignored, leading to empty configs being used. Trading commands may proceed with no account config rather than failing clearly.
- Fix approach: Replace `except:` with `except Exception:` at minimum. For config-loading sections, log the error and fail loudly rather than proceeding with defaults.

### Inconsistent `_load_json` / `safe_load_json` Duplication
- Issue: At least 4 different implementations of "load JSON file with fallback": `_load_json()` in `generate_ai_decision_response.py`, `load_json()` in `diag_state_sources.py`, `safe_load_json()` in `etf_core/state_io.py`, and ad-hoc inline patterns.
- Files: `skills/ETF_TW/scripts/generate_ai_decision_response.py` (lines 18-25), `skills/ETF_TW/scripts/diag_state_sources.py` (lines 27-33), `skills/ETF_TW/scripts/etf_core/state_io.py` (lines 11-20), `skills/ETF_TW/scripts/state_reconciliation_enhanced.py` (lines 34-41)
- Impact: Different error handling behavior across the codebase. Some catch all exceptions silently, some use `atomic_save_json` for writes but not reads.
- Fix approach: Consolidate to `etf_core/state_io.py`'s `safe_load_json` / `atomic_save_json` everywhere. Remove all inline re-implementations.

## Known Bugs

### `api.logout()` Segfault
- Symptoms: Calling `api.logout()` on Shioaji causes a process segfault (crash).
- Files: `skills/ETF_TW/scripts/sync_macro_indicators.py` (line 69), `skills/ETF_TW/scripts/diag_shioaji_contracts.py` (line 40)
- Trigger: Any script that calls `api.logout()` after a Shioaji session will crash the process.
- Workaround: Never call `api.logout()`. Let the process exit naturally.

### `api.stock_account` Property Misuse
- Symptoms: `api.stock_account` is a **property**, not a method. Calling it with `()` raises `TypeError`.
- Files: `skills/ETF_TW/scripts/adapters/sinopac_adapter.py` (line 460: `account=self.api.stock_account`)
- Trigger: If code anywhere incorrectly uses `self.api.stock_account()`, it crashes at runtime during order submission.
- Workaround: Always use `self.api.stock_account` without parentheses.

### Broker Order ID Field Confusion
- Symptoms: Shioaji stores the broker order ID in `trade.order.ordno`, NOT in `trade.status.order_id`. Using the wrong field silently records an empty or incorrect order ID.
- Files: `skills/ETF_TW/scripts/adapters/sinopac_adapter.py` (line 468: uses `trade.status.order_id`)
- Trigger: Any SinoPac live trade where `trade.status.order_id` is empty but `trade.order.ordno` has the real ID.
- Workaround: Always read `trade.order.ordno` for the broker order ID per Shioaji API contract.

### Ghost Order False Positives
- Symptoms: Orders with `broker_order_id: null`, `verified: false`, and `order_id: ""` are phantom entries that should never be reported as placed. Reporting them as placed would show the user a fake order.
- Files: Concern spans `skills/ETF_TW/scripts/complete_trade.py`, `skills/ETF_TW/scripts/orders_open_state.py`, `skills/ETF_TW/scripts/orders_open_callback.py`
- Trigger: A submit attempt that fails at the SinoPac API level but the response is still recorded.
- Workaround: Check for ghost order pattern before reporting any order status. A ghost order fails all three conditions: null broker_order_id AND verified=false AND empty order_id.

### Market Close Check Uses Local Time
- Symptoms: `poll_order_status.py` (line 136) checks market close using `datetime.now()` without timezone, potentially stopping polling early or late if the system timezone is not Asia/Taipei.
- Files: `skills/ETF_TW/scripts/poll_order_status.py` (lines 135-138)
- Trigger: Running the polling script from a non-Taiwan timezone.
- Workaround: Use `datetime.now(ZoneInfo('Asia/Taipei'))` like `trading_hours_gate.py` does.

## Security Considerations

### `instance_config.json` World-Readable
- Risk: Instance config is readable by all users on the machine. It may contain broker account IDs, API key references, and account routing details.
- Files: `skills/ETF_TW/instances/etf_master/instance_config.json` (permissions: 644)
- Current mitigation: `.gitignore` excludes `instances/`. API keys are stored in `.env` (600) and `private/.env` (600), not directly in this file.
- Recommendations: Set permissions to 600. Add a startup check that warns if sensitive config files are group/other readable.

### State Files with Overly Permissive Permissions
- Risk: Several instance state files have 644 permissions (world-readable). `auto_trade_submissions.json`, `news_articles.json`, and `market_intelligence.json` may contain trade-related data.
- Files: `skills/ETF_TW/instances/etf_master/state/auto_trade_submissions.json` (644), `skills/ETF_TW/instances/etf_master/state/family_identity.json` (644), `skills/ETF_TW/instances/etf_master/state/market_intelligence.json` (644), `skills/ETF_TW/instances/etf_master/state/news_articles.json` (644)
- Current mitigation: `.gitignore` excludes `instances/`. Most other state files already use 600.
- Recommendations: Set all state files to 600. Add a permissions check in `sync_*` scripts to enforce 600 on write.

### Shioaji API Keys in `private/.env` Read via Python
- Risk: The Hermes `read_file()` tool masks API keys as `***`. For scripts that need real credential values, they read `private/.env` using Python `open()` + `line.split('=', 1)`. This is correct but relies on the `.env` file never being accidentally committed or displayed.
- Files: `skills/ETF_TW/private/.env`, `skills/ETF_TW/scripts/complete_trade.py` (lines 29-36)
- Current mitigation: `.gitignore` excludes `private/` and `.env`. File permissions are 600.
- Recommendations: Consider using Python `keyring` or OS keychain for API keys instead of flat `.env` files.

### DNS Monkey-Patch (`dns_fix.py`)
- Risk: `dns_fix.py` monkey-patches `socket.getaddrinfo` when system DNS is broken. This replaces a core networking function globally. If the patched version has bugs, ALL network requests in the process are affected.
- Files: `skills/ETF_TW/scripts/dns_fix.py` (lines 132-175)
- Current mitigation: Patch only activates when system DNS test fails. Normal state does not trigger it. Has a 100-entry cache and timeout.
- Recommendations: Remove once sandbox DNS issues are permanently resolved. The `/etc/hosts` entries already exist as of 2026-04-14. Currently only needed as extreme fallback.

### `get_adapter()` Does Not Register `sinopac_adapter_enhanced`
- Risk: `base.py:get_adapter()` (line 175-194) only maps `'sinopac'` to `SinopacAdapter`, not `SinopacAdapterEnhanced`. If someone configures `broker_id: 'sinopac_enhanced'`, they get a `ValueError`.
- Files: `skills/ETF_TW/scripts/adapters/base.py` (lines 175-194)
- Current mitigation: The enhanced adapter is not currently referenced in any `broker_registry.json` entry.
- Recommendations: Either register the enhanced adapter in `get_adapter()` or delete it entirely (see duplicate adapter debt above).

## Performance Bottlenecks

### `dashboard_manager.log` Unbounded Growth (107 MB)
- Problem: The dashboard manager writes logs continuously every 30 seconds and never rotates or truncates the log file.
- Files: `skills/ETF_TW/instances/dashboard_manager.log` (107 MB, 1.6M lines)
- Cause: `dashboard_guard.py` runs an infinite health-check loop with `time.sleep(CHECK_INTERVAL=30)`. Each check appends log lines.
- Improvement path: Add log rotation (e.g., `RotatingFileHandler` with max size). Purge existing 107 MB log. Consider reducing check frequency for healthy instances.

### Unbounded JSONL Growth (Append-Only State Files)
- Problem: Multiple `.jsonl` files grow without pruning: `decision_log.jsonl`, `decision_outcomes.jsonl`, `decision_provenance.jsonl`, `decision_review.jsonl`, `ai_decision_reflection.jsonl`, `layered_review_plan.jsonl`, `layered_review_registrations.jsonl`.
- Files: `skills/ETF_TW/instances/etf_master/state/decision_log.jsonl` (32 KB), `skills/ETF_TW/instances/etf_master/state/decision_outcomes.jsonl`, `skills/ETF_TW/instances/etf_master/state/layered_review_plan.jsonl` (19 KB), `skills/ETF_TW/instances/etf_master/state/layered_review_registrations.jsonl` (16 KB)
- Cause: `safe_append_jsonl()` in `etf_core/state_io.py` always appends. No rotation, compaction, or archival logic exists.
- Improvement path: Add periodic compaction (e.g., keep last N days, archive older entries). Implement in a new `sync_compact_state.py` script.

### Growing `ai_decision_request.json` (88 KB for a single file)
- Problem: `ai_decision_request.json` accumulates full market intelligence snapshots on each decision cycle. At 88 KB per write, frequent decision scans will keep it growing.
- Files: `skills/ETF_TW/instances/etf_master/state/ai_decision_request.json` (88 KB)
- Cause: `generate_ai_decision_request.py` embeds full `market_intelligence.json` (160 KB) into the request payload.
- Improvement path: Store only references (symbol list) in the request, not the full intelligence payload. Downstream scripts can load `market_intelligence.json` separately.

### `market_intelligence.json` Full Rewrite Every Sync
- Problem: `market_intelligence.json` (160 KB) is rewritten in full each time market cache syncs, even if only a few symbols changed.
- Files: `skills/ETF_TW/instances/etf_master/state/market_intelligence.json` (160 KB)
- Cause: Sync scripts load the entire file, merge, and write back. No incremental update.
- Improvement path: Acceptable for now given file size, but consider incremental writes if the watchlist grows significantly.

## Fragile Areas

### Order Event Precedence (`choose_preferred_row`)
- Files: `skills/ETF_TW/scripts/order_event_precedence.py` (lines 74-121)
- Why fragile: The 4-layer precedence logic (status rank > timestamp > broker_seq > source priority) is complex. The function uses `type("Order", (), row)()` to create a mock object on line 78-80 and line 51 of `orders_open_state.py`. If the `row` dict has unexpected keys, `getattr()` may return stale or incorrect values.
- Safe modification: Always add new test cases in `tests/test_order_event_*.py` before modifying precedence rules. The mock-object pattern `type("Order", (), row)()` should be replaced with direct dict access.
- Test coverage: Good (7+ test files for precedence), but the mock-object hack could mask bugs.

### Dual State Location (Root `state/` vs Instance `instances/<id>/state/`)
- Files: `skills/ETF_TW/state/` (root, legacy), `skills/ETF_TW/instances/etf_master/state/` (canonical)
- Why fragile: The legacy `state/` directory still exists with a symlink (`state_legacy_compat_link`). Scripts that accidentally read from root state get stale data. `diag_state_sources.py` detects "ROOT_LEAK" when root state files exist.
- Safe modification: Never add new files to root `state/`. Always use `context.get_state_dir()`. The root `state/` directory contains only `README.md`, `auto_trade_state.json`, and `trading_mode.json` (likely stale copies).
- Test coverage: `tests/test_instance_state_paths.py` checks that scripts do not contain forbidden root-state patterns.

### Shioaji Login State
- Files: `skills/ETF_TW/scripts/adapters/sinopac_adapter.py` (lines 54-80)
- Why fragile: The adapter reads `api_key` and `secret_key` from config, but the Shioaji SDK also supports `person_id` + `password` login. The `authenticate()` method uses API key login. If Shioaji changes their SDK or deprecates API key auth, this breaks. Additionally, `stock_account` is auto-selected heuristically with hardcoded `account_id == "0737121"` (line 73 in the enhanced adapter).
- Safe modification: When modifying auth flow, test both paper and live modes. Never hardcode account IDs.
- Test coverage: `scripts/test_sinopac.py` exists but is in the scripts directory, not in the formal test suite under `tests/`.

### Trading Hours Gate (`check_trading_hours_gate()` calls `sys.exit()`)
- Files: `skills/ETF_TW/scripts/trading_hours_gate.py` (line 58)
- Why fragile: The gate function calls `sys.exit(1)` directly, which cannot be caught by normal `try/except`. This makes it impossible to use in a larger workflow that wants to handle the rejection gracefully.
- Safe modification: Use the `is_trading_hours()` boolean variant instead. Refactor `check_trading_hours_gate()` to raise a custom exception instead of `sys.exit()`.
- Test coverage: Partial. `is_trading_hours()` is testable, but `check_trading_hours_gate()` is not safely testable since it calls `sys.exit()`.

### `orders_open_state.py` Line 52: Mock Object Pattern
- Files: `skills/ETF_TW/scripts/orders_open_state.py` (line 52)
- Why fragile: `[row for row in merged if not order_terminal(type("Order", (), row)())]` creates a throwaway class from a dict. If a row is missing the `status` key, `getattr(order, "status", None)` returns `None`, which `normalize_order_status` converts to `"pending"` -- meaning incomplete orders survive the terminal filter accidentally.
- Safe modification: Replace with `not order_terminal(row)` after refactoring `order_terminal()` to accept dicts directly.
- Test coverage: `tests/test_orders_open_contract.py` and `tests/test_orders_open_state_helper.py` exist.

## Scaling Limits

### Single-Broker Adapter Registration
- Current capacity: `get_adapter()` in `base.py` maps only `paper` and `sinopac` (with optional `cathay`). But `broker_registry.json` lists 5+ brokers including `yuanlin`.
- Limit: Adding a new broker requires importing its adapter manually in `base.py` and adding it to `adapter_map`. The optional import pattern (`try: from .cathay_adapter import CathayAdapter; adapter_map['cath'] = CathayAdapter; except ImportError: pass`) on line 187 is fragile.
- Scaling path: Use entry-point-based adapter discovery. Load adapters from `broker_registry.json` dynamically rather than hardcoding imports.

### Risk Controller In-Memory State
- Current capacity: `RiskController` stores `order_history` as an in-memory list (max 1000 entries, line 203 in `risk_controller.py`). If the process restarts, all duplicate detection history is lost.
- Limit: After restart, duplicate orders within the 5-minute window will not be detected.
- Scaling path: Persist order history to a JSONL file or SQLite. Load recent history on startup.

### No Concurrent Access Protection on State Files
- Current capacity: Multiple scripts can write to the same state file simultaneously (e.g., cron-triggered sync scripts + dashboard-initiated refreshes). `atomic_save_json` prevents partial writes but does not prevent race conditions between reads and writes.
- Limit: Two concurrent writes to the same file may cause one to be lost (last-writer-wins with no lock).
- Scaling path: Add file-level locking (e.g., `filelock` library) for critical state files like `orders_open.json` and `positions.json`.

## Dependencies at Risk

### Shioaji SDK
- Risk: Proprietary SDK with no public source. API changes are undocumented and can break the adapter without warning. Known API pitfalls (property vs method on `stock_account`, segfault on `logout()`) suggest instability.
- Impact: Both `sinopac_adapter.py` and `sinopac_adapter_enhanced.py` would break. Live trading would be impossible until adapter is fixed.
- Migration plan: Wrap all Shioaji API calls in a thin abstraction layer. When API changes break things, only the abstraction layer needs updating. Keep a `shioaji_api_reference.md` updated with every discovered pitfall.

### yfinance
- Risk: yfinance is an unofficial scraping library for Yahoo Finance. It can break silently when Yahoo changes their HTML/API. The suffix convention (`.TW` vs `.TWO`) is critical and easy to get wrong.
- Impact: Market data sync (`sync_market_cache.py`), backfill (`backfill_outcomes.py`), and `MarketDataProvider.get_price()` in `base.py` all depend on it.
- Migration plan: Consider adding a secondary data source (e.g., TWSE open data API) as fallback. Already partially addressed by Shioaji snapshots as primary.

## Missing Critical Features

### No Log Rotation for Any State/Log File
- Problem: No automated cleanup or rotation exists for the 107 MB dashboard manager log, growing JSONL files, or the 112 KB `shioaji.log` at the root.
- Blocks: Long-running production usage will fill disk. State files that grow without bound will eventually slow down `safe_load_jsonl()`.

### No Automated State Compaction
- Problem: `safe_append_jsonl()` always appends. No script compacts, archives, or prunes old entries.
- Blocks: Over months of operation, decision logs and provenance records will accumulate indefinitely.

### Non-Financial Skills Have No Tests
- Problem: `stock-analysis-tw`, `stock-market-pro-tw`, `taiwan-finance`, and the `opencli-*` skills have zero test files. Only ETF_TW has ~150 test files.
- Blocks: Any change to these skills risks silent breakage. They are completely untested.

### No Health Check for Broker Connectivity
- Problem: The `RiskController` circuit breaker status (lines 210-222) returns hardcoded `False` for `daily_loss_limit` and `market_halt` with comments like "Would need PnL tracking" and "Would need market data".
- Blocks: Circuit breakers cannot actually trigger. The risk system is advisory only, not protective.

## Test Coverage Gaps

### Adapter Live Integration Tests Not in Formal Suite
- What's not tested: `scripts/test_sinopac.py`, `scripts/test_cathay.py`, `scripts/test_yuanlin.py`, and `scripts/test_phase4.py` are in the `scripts/` directory, not under `tests/`. They are not discovered by `python -m pytest tests/`.
- Files: `skills/ETF_TW/scripts/test_sinopac.py`, `skills/ETF_TW/scripts/test_cathay.py`, `skills/ETF_TW/scripts/test_yuanlin.py`, `skills/ETF_TW/scripts/test_phase4.py`
- Risk: Adapter integration tests are not run as part of the standard test suite. Regressions go undetected.
- Priority: High

### `complete_trade.py` Order Submission Path
- What's not tested: The critical path from order validation through submit, verification, and poll has tests for individual components but no end-to-end integration test that verifies the full submit-verify-record cycle.
- Files: `skills/ETF_TW/scripts/complete_trade.py` (364 lines)
- Risk: A bug in the submission-to-verification handoff could cause ghost orders (reported as placed but never actually submitted to the broker).
- Priority: High

### Market Close Detection in `poll_order_status.py`
- What's not tested: The market close check on line 136 uses `datetime.now()` without timezone, unlike the rest of the codebase which uses `ZoneInfo('Asia/Taipei')`.
- Files: `skills/ETF_TW/scripts/poll_order_status.py` (lines 135-138)
- Risk: Polling stops early or late when run from a non-Taiwan timezone.
- Priority: Medium

### Non-ETF_TW Financial Skills
- What's not tested: `stock-analysis-tw`, `stock-market-pro-tw`, `taiwan-finance` have zero test files.
- Files: `skills/stock-analysis-tw/`, `skills/stock-market-pro-tw/`, `skills/taiwan-finance/`
- Risk: Any refactor or API change silently breaks analysis, charts, or valuation output.
- Priority: Medium

### Dashboard API Endpoints
- What's not tested: While dashboard has many test files (~30+), most are template/content tests. The actual API route handlers for order submission, strategy updates, and trading mode changes lack integration tests.
- Files: `skills/ETF_TW/dashboard/app.py` (1160 lines)
- Risk: API contract changes (e.g., adding a required field to `AutoTradeSubmitRequest`) may not be caught by existing tests.
- Priority: Medium

---

*Concerns audit: 2026-04-15*