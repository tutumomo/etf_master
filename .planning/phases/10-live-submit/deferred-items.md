# Deferred Items — Phase 10 live-submit

## Out-of-scope discoveries (do NOT fix in this phase)

### 1. subprocess.Popen with shell=True (CWE-78)
- **Files:** `skills/ETF_TW/dashboard/app.py` lines 1197, 1238
- **Discovered during:** Plan 10-05 execution (semgrep post-edit scan)
- **Severity:** ERROR (semgrep)
- **Note:** Pre-existing code, not introduced by 10-05. Dashboard runs localhost-only.
  Fix in a future hardening plan: replace shell=True with shell=False + shlex.split().

### 2. test_sinopac_adapter_live_submit.py — 5 pre-existing failures
- **Tests:** test_pre_flight_gate_fail_blocks_submit, test_verified_order_written_to_orders_open,
  test_ghost_order_not_written_to_orders_open, test_live_mode_disabled_rejects_immediately,
  test_adapter_exception_returns_graceful_error
- **Discovered during:** Plan 10-05 full suite run
- **Note:** Pre-existing failures unrelated to 10-05 changes.
