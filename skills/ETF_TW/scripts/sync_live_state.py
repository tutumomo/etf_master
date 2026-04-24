#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from account_manager import get_account_manager
from trading_mode import read_trading_mode_state

try:
    from shioaji.constant import Unit
except Exception:
    Unit = None

import sys
ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

# Multi-tenant Context
STATE_DIR = context.get_state_dir()
POSITIONS_STATE_PATH = STATE_DIR / "positions.json"
ACCOUNT_STATE_PATH = STATE_DIR / "account_snapshot.json"
INSTANCE_CONFIG_PATH = context.get_instance_config()


def should_sync_live_state(mode_state: dict) -> bool:
    return mode_state.get("effective_mode") == "live-ready"


def build_live_positions_payload(positions, updated_at: str) -> dict:
    return {
        "positions": [
            {
                "symbol": getattr(p, "symbol", None),
                "quantity": getattr(p, "quantity", None),
                "average_price": getattr(p, "average_price", None),
                "current_price": getattr(p, "current_price", None),
                "market_value": getattr(p, "market_value", None),
                "unrealized_pnl": getattr(p, "unrealized_pnl", None),
                "source": "live_broker",
            }
            for p in positions
        ],
        "updated_at": updated_at,
        "source": "live_broker",
    }


def normalize_settlement_row(row) -> dict:
    return {
        "date": str(getattr(row, "date", "")),
        "T": int(getattr(row, "T", 0) or 0),
        "amount": float(getattr(row, "amount", 0) or 0),
        "source": "live_broker_settlements",
    }


def build_settlement_safety(cash: float, settlements: list[dict] | None) -> dict:
    rows = settlements or []
    future_rows = [row for row in rows if int(row.get("T", 0) or 0) in (1, 2)]
    future_net = round(sum(float(row.get("amount", 0) or 0) for row in future_rows), 2)
    safe_cash = round(float(cash or 0) + future_net, 2)
    return {
        "settlements": rows,
        "future_settlement_net_t1_t2": future_net,
        "settlement_safe_cash": safe_cash,
        "settlement_safe_cash_floor": max(0, safe_cash),
        "settlement_safe_cash_formula": "cash + T1/T2 settlement net",
        "settlement_safe_cash_note": "扣除未來 T+1/T+2 淨交割款後的交割安全金額；未扣額外安全緩衝。",
    }


def build_live_account_snapshot(balance, position_count: int, updated_at: str, positions=None, settlements=None, settlements_error: str | None = None) -> dict:
    api_market_value = float(getattr(balance, "market_value", 0) or 0)
    # Shioaji API returns 0 for market_value; compute from positions if available
    if api_market_value == 0 and positions:
        calculated_mv = sum(
            float(getattr(p, "market_value", 0) or 0)
            for p in positions
        )
        # If position-level market_value is also 0, fallback to qty × current_price
        if calculated_mv == 0:
            calculated_mv = sum(
                float(getattr(p, "quantity", 0) or 0) * float(getattr(p, "current_price", 0) or 0)
                for p in positions
            )
        api_market_value = round(calculated_mv, 2)

    cash = float(getattr(balance, "cash_available", 0) or 0)
    api_total_equity = float(getattr(balance, "total_value", 0) or 0)
    # If API total_equity is 0 or only reflects cash, recompute from cash + market_value
    if api_total_equity == 0 and api_market_value > 0:
        api_total_equity = round(cash + api_market_value, 2)

    settlement_payload = build_settlement_safety(cash, settlements)
    if settlements_error:
        settlement_payload["settlements_error"] = settlements_error

    return {
        "cash": cash,
        "market_value": api_market_value,
        "total_equity": api_total_equity,
        "updated_at": updated_at,
        "source": "live_broker",
        "position_count": position_count,
        **settlement_payload,
    }


async def main() -> int:
    mode_state = read_trading_mode_state()
    if not should_sync_live_state(mode_state):
        print("LIVE_STATE_SYNC_SKIPPED")
        return 0

    # Load account manager with instance-specific config
    manager = get_account_manager(str(INSTANCE_CONFIG_PATH))
    account_alias = mode_state.get("default_account") or manager.get_config().get("default_account")
    account = manager.get_account(account_alias)
    adapter = manager.get_adapter(account_alias)

    if not await adapter.authenticate():
        raise RuntimeError("live adapter authentication failed")

    balance = await adapter.get_account_balance(account.get("account_id"))
    settlements = []
    settlements_error = None
    try:
        api = getattr(adapter, "api", None)
        stock_account = getattr(adapter, "stock_account", None) or getattr(api, "stock_account", None)
        if api is not None and stock_account is not None:
            settlements = [normalize_settlement_row(row) for row in api.settlements(stock_account)]
        else:
            settlements_error = "live adapter does not expose Shioaji settlements API"
    except Exception as e:
        settlements_error = str(e)

    # 直接呼叫適配器的標準介面，內部的 SinopacAdapter 已處理完畢 Unit.Share 參數
    positions = await adapter.get_positions(account.get("account_id"))
    updated_at = datetime.now().isoformat()

    POSITIONS_STATE_PATH.write_text(json.dumps(build_live_positions_payload(positions, updated_at), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ACCOUNT_STATE_PATH.write_text(json.dumps(build_live_account_snapshot(balance, len(positions), updated_at, positions=positions, settlements=settlements, settlements_error=settlements_error), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_STATE_SYNC_OK")
    return 0


if __name__ == "__main__":
    # NOTE: shioaji may spawn background threads; in some environments Python finalization can SIGABRT
    # (gilstate_tss_set: failed to set current tstate). Use os._exit to avoid interpreter finalization crashes.
    import os
    code = 0
    try:
        code = int(asyncio.run(main()) or 0)
    except SystemExit as e:
        try:
            code = int(e.code or 0)
        except Exception:
            code = 1
    except Exception:
        code = 1
        raise
    finally:
        os._exit(code)
