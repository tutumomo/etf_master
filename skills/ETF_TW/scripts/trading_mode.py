#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

# Multi-tenant Context
STATE_DIR = context.get_state_dir()
TRADING_MODE_PATH = STATE_DIR / "trading_mode.json"


def has_live_credentials(config: dict[str, Any]) -> bool:
    accounts = config.get("accounts", {}) or {}
    brokers = config.get("brokers", {}) or {}
    for account in accounts.values():
        if str(account.get("mode") or "").lower() != "live":
            continue
        account_id = account.get("account_id")
        credentials = account.get("credentials", {}) or {}
        broker_id = account.get("broker_id")
        broker = brokers.get(broker_id, {}) if broker_id else {}
        api_key = credentials.get("api_key") or broker.get("api_key")
        api_secret = credentials.get("api_secret") or credentials.get("secret_key") or broker.get("secret_key")
        if account_id and api_key and api_secret:
            return True
    return False


def resolve_effective_mode(config: dict[str, Any], manual_override: str | None, live_check_ok: bool, previous_mode: str = "paper") -> dict[str, Any]:
    live_capable = has_live_credentials(config)
    effective_mode = "paper"
    data_source = "paper_ledger"
    message = "paper default"
    health_ok = True  # Paper mode is usually always "healthy" if ledger exists

    if manual_override == "paper":
        effective_mode = "paper"
        data_source = "paper_ledger"
        message = "manual override to paper"
        health_ok = True
    elif manual_override == "live":
        if live_capable and live_check_ok:
            effective_mode = "live-ready"
            data_source = "live_broker"
            message = "manual override to live-ready"
            health_ok = True
        else:
            effective_mode = previous_mode or "paper"
            # If we failed to switch to live, or previous mode was live and now failing
            data_source = "live_broker" if effective_mode == "live-ready" else "paper_ledger"
            message = "live connection failed; falling back to " + effective_mode
            # Fix: If user manually asked for live but it failed, it's NOT healthy even if fallback to paper.
            health_ok = False
    else:
        # Auto-detect logic
        if live_capable and live_check_ok:
            effective_mode = "live-ready"
            data_source = "live_broker"
            message = "auto-detected live-ready"
            health_ok = True
        else:
            effective_mode = "paper"
            data_source = "paper_ledger"
            message = "auto-detected paper (no live credentials or check failed)"
            health_ok = True

    return {
        "effective_mode": effective_mode,
        "manual_override": manual_override,
        "live_capable": live_capable,
        "health_check_ok": health_ok,
        "data_source": data_source,
        "health_check_message": message,
    }


def read_trading_mode_state(path: Path | None = None) -> dict[str, Any]:
    target = path or TRADING_MODE_PATH
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def write_trading_mode_state(path: Path | None, payload: dict[str, Any]) -> dict[str, Any]:
    target = path or TRADING_MODE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    final_payload = {**payload, "updated_at": payload.get("updated_at") or datetime.now().isoformat()}
    target.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return final_payload
