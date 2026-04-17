# Daily Submit Quota Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add daily live-submit buy/sell quotas to Safety Redlines so the agent can only send a limited number of real broker orders per day, regardless of fill outcome.

**Architecture:** Store quota settings in `safety_redlines.json`, store day-scoped counters in a new `daily_order_limits.json`, enforce limits in `pre_flight_gate.py`, and increment counters only after successful live submit in `live_submit_sop.py`. Surface both settings and current usage in the dashboard Safety Redlines card.

**Tech Stack:** Python, FastAPI, JSON state files, existing ETF_TW dashboard templates, pytest/unittest-style regression tests

---

### Task 1: Add quota settings to Safety Redlines defaults

**Files:**
- Modify: `skills/ETF_TW/scripts/sync_daily_pnl.py`
- Modify: `skills/ETF_TW/dashboard/app.py`

**Step 1: Write the failing test**

Add or update a test file to assert the default Safety Redlines payload includes:

```python
assert redlines["daily_max_buy_submits"] == 2
assert redlines["daily_max_sell_submits"] == 2
```

**Step 2: Run test to verify it fails**

Run: `cd skills/ETF_TW && .venv/bin/python3 -m pytest tests/ -k "safety_redlines and default" -q`

Expected: FAIL because the new keys do not exist yet.

**Step 3: Write minimal implementation**

Update default redline dictionaries in both modules to include:

```python
"daily_max_buy_submits": 2,
"daily_max_sell_submits": 2,
```

**Step 4: Run test to verify it passes**

Run the same command and confirm the new default-key assertion passes.

**Step 5: Commit**

```bash
git add skills/ETF_TW/scripts/sync_daily_pnl.py skills/ETF_TW/dashboard/app.py tests/...
git commit -m "feat(redlines): add daily submit quota defaults"
```

### Task 2: Add daily order quota state helper

**Files:**
- Create: `skills/ETF_TW/scripts/daily_order_limits.py`
- Test: `skills/ETF_TW/tests/test_daily_order_limits.py`

**Step 1: Write the failing test**

Create tests for:

- missing file initializes with today’s date and zero counts
- same-day load preserves counts
- date rollover resets counts to zero

Example:

```python
def test_rollover_resets_counts(tmp_path):
    ...
    assert data["buy_submit_count"] == 0
    assert data["sell_submit_count"] == 0
```

**Step 2: Run test to verify it fails**

Run: `cd skills/ETF_TW && .venv/bin/python3 -m pytest tests/test_daily_order_limits.py -q`

Expected: FAIL because helper module does not exist.

**Step 3: Write minimal implementation**

Implement helper functions:

- `load_daily_order_limits(...)`
- `ensure_daily_order_limits(...)`
- `increment_daily_submit_count(side, ...)`

Keep JSON shape:

```python
{
    "date": today,
    "buy_submit_count": 0,
    "sell_submit_count": 0,
    "last_updated": iso_ts,
}
```

**Step 4: Run test to verify it passes**

Run the same test command and confirm all helper tests pass.

**Step 5: Commit**

```bash
git add skills/ETF_TW/scripts/daily_order_limits.py skills/ETF_TW/tests/test_daily_order_limits.py
git commit -m "feat(redlines): add daily order quota state helper"
```

### Task 3: Enforce quota limits in pre-flight gate

**Files:**
- Modify: `skills/ETF_TW/scripts/pre_flight_gate.py`
- Test: `skills/ETF_TW/tests/test_safety_redlines.py`

**Step 1: Write the failing test**

Add tests:

- buy side over quota returns `daily_buy_submit_limit_reached`
- sell side over quota returns `daily_sell_submit_limit_reached`

Example:

```python
assert result["reason"] == "daily_buy_submit_limit_reached"
```

**Step 2: Run test to verify it fails**

Run: `cd skills/ETF_TW && .venv/bin/python3 -m pytest tests/test_safety_redlines.py -q`

Expected: FAIL because gate does not yet inspect daily submit counters.

**Step 3: Write minimal implementation**

Extend safety-data loading so gate can read:

- redline settings
- current daily order counts

Then enforce:

```python
if side == "buy" and buy_count >= daily_max_buy_submits:
    return _fail("daily_buy_submit_limit_reached", ...)
if side == "sell" and sell_count >= daily_max_sell_submits:
    return _fail("daily_sell_submit_limit_reached", ...)
```

**Step 4: Run test to verify it passes**

Run the same test file and confirm quota tests pass without regressing existing redline tests.

**Step 5: Commit**

```bash
git add skills/ETF_TW/scripts/pre_flight_gate.py skills/ETF_TW/tests/test_safety_redlines.py
git commit -m "feat(redlines): enforce daily submit quotas in pre-flight gate"
```

### Task 4: Increment counters only after successful live submit

**Files:**
- Modify: `skills/ETF_TW/scripts/live_submit_sop.py`
- Modify: `skills/ETF_TW/tests/test_sinopac_adapter_live_submit.py`

**Step 1: Write the failing test**

Add tests for:

- successful buy submit increments `buy_submit_count`
- successful sell submit increments `sell_submit_count`
- failed submit does not increment
- ghost/verification failure behavior is explicitly asserted based on desired policy

Example:

```python
assert updated["buy_submit_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `cd skills/ETF_TW && .venv/bin/python3 -m pytest tests/test_sinopac_adapter_live_submit.py -q`

Expected: FAIL because no quota mutation happens today.

**Step 3: Write minimal implementation**

In the live submit success path, after broker submit succeeds:

- increment the matching side counter
- persist the updated daily quota state

Do not increment when:

- gate blocks before submit
- submit raises/returns failure

**Step 4: Run test to verify it passes**

Run the same file and confirm live submit quota mutations are correct.

**Step 5: Commit**

```bash
git add skills/ETF_TW/scripts/live_submit_sop.py skills/ETF_TW/tests/test_sinopac_adapter_live_submit.py
git commit -m "feat(redlines): count successful live submits against daily quota"
```

### Task 5: Expose settings and usage in dashboard APIs

**Files:**
- Modify: `skills/ETF_TW/dashboard/app.py`
- Test: `skills/ETF_TW/tests/test_dashboard_trading_mode_api.py`
- Test: add new dashboard API contract test if needed

**Step 1: Write the failing test**

Assert dashboard payload includes:

- `daily_max_buy_submits`
- `daily_max_sell_submits`
- current usage counts from daily order limits state

Example:

```python
assert body["safety_redlines"]["daily_max_buy_submits"] == 2
assert body["daily_order_limits"]["buy_submit_count"] == 1
```

**Step 2: Run test to verify it fails**

Run the relevant dashboard API test file.

Expected: FAIL because the response does not yet include quota usage state.

**Step 3: Write minimal implementation**

Load `daily_order_limits.json` in dashboard app and pass it to template / API response context.

**Step 4: Run test to verify it passes**

Run the targeted dashboard API tests and confirm payload shape is stable.

**Step 5: Commit**

```bash
git add skills/ETF_TW/dashboard/app.py skills/ETF_TW/tests/...
git commit -m "feat(dashboard): expose daily submit quota settings and usage"
```

### Task 6: Add dashboard controls for the new quota settings

**Files:**
- Modify: `skills/ETF_TW/dashboard/templates/overview.html`
- Test: add/update template presence tests under `skills/ETF_TW/tests/`

**Step 1: Write the failing test**

Assert template contains:

- buy quota input
- sell quota input
- current usage readout text

**Step 2: Run test to verify it fails**

Run the targeted template test file.

Expected: FAIL because the new controls do not exist yet.

**Step 3: Write minimal implementation**

Add two inputs to the Safety Redlines card:

- `每日可下單買入次數`
- `每日可下單賣出次數`

Add current usage display, e.g.:

```html
今日買入已送出：{{ daily_order_limits.get('buy_submit_count', 0) }} / {{ safety_redlines.get('daily_max_buy_submits', 2) }}
```

Update `saveSafetyRedlines()` payload to include both new fields.

**Step 4: Run test to verify it passes**

Run the targeted template test file and confirm the new controls exist.

**Step 5: Commit**

```bash
git add skills/ETF_TW/dashboard/templates/overview.html skills/ETF_TW/tests/...
git commit -m "feat(dashboard): add daily submit quota controls to safety redlines"
```

### Task 7: Run focused verification and full regression

**Files:**
- No code changes required unless a regression is found

**Step 1: Run focused test groups**

Run:

```bash
cd skills/ETF_TW
.venv/bin/python3 -m pytest tests/test_daily_order_limits.py -q
.venv/bin/python3 -m pytest tests/test_safety_redlines.py -q
.venv/bin/python3 -m pytest tests/test_sinopac_adapter_live_submit.py -q
```

Expected: PASS

**Step 2: Run dashboard smoke verification**

Run:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5055/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5055/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5055/api/overview
```

Expected: all `200`

**Step 3: Run full suite**

Run:

```bash
cd skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q
```

Expected: existing suite stays green.

**Step 4: Commit final verification or fixes**

```bash
git add ...
git commit -m "test(redlines): verify daily submit quota integration"
```
