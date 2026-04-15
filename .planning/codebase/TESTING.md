# Testing

**Analysis Date:** 2026-04-15

## Framework

- **pytest 9.0.2** — Primary and only test framework
- **No conftest.py** — Tests lack shared fixtures; each test file is self-contained
- **No pytest plugins** — No pytest-cov, pytest-mock, pytest-asyncio, or similar
- **No CI pipeline** — Tests run manually via command line

## Test Structure

### Location
- **All tests:** `skills/ETF_TW/tests/`
- **Count:** ~144 test files, ~247 individual test functions
- **Other skills:** No test files found in stock-analysis-tw, stock-market-pro-tw, taiwan-finance

### File Naming
- **Convention:** `test_<feature>_<aspect>.py`
- **Examples:**
  - `test_ai_decision_bridge_contract.py` — Decision bridge contract tests
  - `test_poll_order_status_contract.py` — Order polling contract
  - `test_partial_fill_position_boundary.py` — Partial fill edge cases
  - `test_callback_polling_verification_consistency.py` — Reconciliation tests

### Test Functions
- **Convention:** `test_<specific_behavior>()`
- **No test classes** — All tests are flat functions, not grouped in classes
- **No parametrize** — No use of `@pytest.mark.parametrize`

## Module Loading

Tests load scripts via `importlib.util` + `sys.path.insert()`:

```python
import importlib.util, sys
sys.path.insert(0, "/path/to/skills/ETF_TW/scripts")
MODULE_PATH = Path("/path/to/skills/ETF_TW/scripts/target_module.py")
spec = importlib.util.spec_from_file_location("target_module", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

This pattern appears in ~all test files because `scripts/` is not a proper Python package.

## Mocking

- **No mocking framework** — No `unittest.mock`, `pytest-mock`, or similar
- **Approach:** Tests call functions with controlled inputs and assert on output structure/fields
- **Contract testing pattern:** Tests verify JSON schema contracts (field presence, types, values)
- **No Shioaji mocking** — Tests avoid calling real API; they test internal logic only
- **No HTTP mocking** — No `responses`, `pytest-httpserver`, or similar libraries

## Coverage

- **No coverage tool** — No pytest-cov, coverage.py, or `.coveragerc`
- **Estimated coverage:** Moderate — core contracts and state reconciliation well-tested; dashboard templates and visualization scripts have minimal testing
- **Uncovered areas:**
  - Dashboard HTML templates
  - Chart generation (stock-market-pro-tw)
  - Stock analysis scripts
  - News crawling
  - Live order submission path (understandably — requires real broker connection)

## Running Tests

```bash
# From ETF_TW directory with venv
cd skills/ETF_TW
.venv/bin/python3 -m pytest tests/ -q                           # Full suite (~3 min)
.venv/bin/python3 -m pytest tests/test_ai_decision_bridge_contract.py -q  # Single file
.venv/bin/python3 -m pytest tests/ -q -k "test_poll_order_status"        # By test name
```

### Known Test Issues
- **No isolation fixtures** — Tests that write to `~/.hermes/` can cause side effects
- **No `conftest.py`** — Each test duplicates the module loading boilerplate
- **Hard-coded paths** — Many tests use absolute paths to the scripts directory
- **No async test support** — Dashboard async endpoints not tested via pytest

## Test Categories

### Contract Tests (~60%)
Verify JSON payload schemas and field contracts:
- `test_ai_decision_bridge_contract.py` — Request/response JSON structure
- `test_ai_decision_bridge_actions.py` — Action field validation
- `test_agent_summary_contract.py` — Summary schema

### Reconciliation Tests (~20%)
Verify broker state reconciliation logic:
- `test_callback_polling_verification_consistency.py`
- `test_broker_seq_precedence.py`
- `test_partial_fill_*` — Edge cases in partial fills

### Integration/State Tests (~15%)
Verify sync scripts and state pipeline:
- `test_sync_live_state.py`
- `test_sync_market_cache.py`
- `test_refresh_pipeline_order.py`

### Dashboard Tests (~5%)
Minimal API endpoint testing:
- `test_dashboard_refresh_api.py`
- `test_dashboard_trading_mode_api.py`
- `test_dashboard_*_panel.py`

---

*Testing analysis: 2026-04-15*