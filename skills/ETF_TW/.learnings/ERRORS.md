# ERRORS.md

## 2026-03-30

### 1) edit tool parameter alias mismatch
- Symptom: `Missing required parameters: oldText alias, newText alias. Supply correct parameters before retrying.`
- Cause: edit call used a mix of parameter names across tool variants.
- Fix: prefer a single canonical parameter set per call (`oldText` + `newText` or the tool's exact accepted aliases) and keep the pair consistent.

### 2) exec `python` not found
- Symptom: `zsh:1: command not found: python`
- Cause: the shell environment does not expose `python` on PATH.
- Fix: use the repo's virtualenv interpreter or `python3`/absolute interpreter path when available.

### 3) SinoPac adapter fallback can select the wrong account
- Symptom: Shioaji login returns multiple accounts, and selecting `accounts[0]` can land on an overseas account instead of the stock account.
- Cause: adapter fallback logic was too loose.
- Fix: prefer configured stock account id, then explicit stock account matching, and do not use blind first-account fallback for balance/position queries.

### 4) Account debug visibility needed for Shioaji login
- Symptom: balance/position failures couldn't be diagnosed because the returned account list was not printed.
- Cause: adapter lacked account list diagnostics.
- Fix: dump returned accounts (id/type/kind/currency) after login and log the selected stock account before account queries.

### 5) Read tool truncation / mis-targeted read invocation
- Symptom: `read` reported a long inline snippet / truncated region instead of the intended next file segment.
- Cause: the requested region likely matched an ambiguous or overly broad area.
- Fix: when reading large files, use tighter offsets/limits or more precise context so the tool can target the intended block cleanly.

### 6) Avoid re-questioning already verified broker-side API status
- Symptom: repeated checks kept treating the broker API as not yet validated even after the user confirmed it was officially opened and tradable.
- Cause: the workflow lagged behind user-confirmed broker-side status.
- Fix: once the user confirms the broker API is live/tradable, treat that as the current baseline and focus on ETF_TW integration gaps only.

### 7) SinoPac adapter config path mismatch for credentials
- Symptom: `Argument 'secret_key' has incorrect type (expected str, got NoneType)` during health/preview/validate tests.
- Cause: `AccountManager` passed `account['credentials']` only if present, but `sinopac_01` stored the keys directly in the top-level `brokers.sinopac` block and used `api_secret` under `accounts.sinopac_01.credentials`, leaving `secret_key` unresolved for adapter config.
- Fix: normalize config assembly so `sinopac` adapter always receives `api_key` and `secret_key` from either broker-level or account-level credential fields with consistent alias mapping.

### 8) Order schema mismatch in account preview/validate flow
- Symptom: `preview-account` / `validate-account` failed with `'dict' object has no attribute 'symbol'`.
- Cause: the account-aware CLI path passed dict orders into adapter methods that expect `Order` dataclass instances.
- Fix: normalize dict orders to the adapter's `Order` dataclass before calling `preview_order` / `validate_order` / `submit_order`.

### 9) Avoid forcing user to perform operator-side checks
- Symptom: wording made it sound like the user had to perform the final submit-preview / operator-side check, even though the intent was for the assistant/operator to run it before sending orders.
- Cause: response phrasing drifted from operator responsibility to user responsibility.
- Fix: when discussing live-submission preparation, clearly state that the assistant/operator performs the final checklist and the user only confirms intent when an actual live submit is about to happen.
