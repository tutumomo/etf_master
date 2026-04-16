# API Integration

## Goal

Prepare `ETF_TW` for future broker connectivity without locking the skill to a single broker or single account.

## Integration rule

This skill must remain safe by default:

- default mode: `paper`
- no silent switch to live mode
- preview and validation come before any future submit path
- the account layer must stay separate from broker-specific transport logic

## Architecture

### Broker registry

Maintain a registry that maps broker ids to adapter implementations, for example:

- `paper`
- `sinopac`
- `cathay`
- future brokers later

### Adapter base interface

Each broker adapter should implement a stable interface such as:

- `get_quote(symbol)`
- `get_account(account_id)`
- `preview_order(order)`
- `submit_order(order)`
- `cancel_order(order_id)`
- `get_order_status(order_id)`
- `list_positions(account_id)`
- `get_cash_balance(account_id)`

### Account registry

Accounts should be configured independently of adapter code.
Each account entry should specify:

- `broker`
- `account_id`
- `mode`
- credential reference
- optional risk overrides

## Order schema

Expected normalized fields:

- `broker` (optional if account alias is used)
- `account`
- `symbol`
- `side`
- `order_type`
- `price`
- `quantity`
- `lot_type`
- `time_in_force`
- `mode`

## Config expectations

Use config fields such as:

- default account alias
- `accounts` map
- broker-specific credential blocks
- sandbox/live flags
- global and per-account risk-check toggles

## Mode separation

### Paper mode

- always allowed
- writes to local paper ledger
- no real broker connectivity required

### Sandbox mode

- only when the broker supports sandbox testing
- still requires preview and validation
- should never be silently treated as live

### Live mode

- future phase only
- requires explicit user intent
- requires stronger safeguards than paper/sandbox

## Integration checklist

Before attaching the first real broker API:

- broker registry exists
- adapter interface is stable
- account schema is stable enough for multiple brokers
- validation is working
- preview is working
- paper trade path is working
- risk controls are documented and enforced
- account-aware CLI routing exists
