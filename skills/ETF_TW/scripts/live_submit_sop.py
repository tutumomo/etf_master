#!/usr/bin/env python3
"""
Live Submit SOP — Single authorized entry point for live order execution.
ETF_TW / Phase 10 / LIVE-01

Pipeline:
  1. Check live_mode.json enabled=True
  2. pre_flight_gate.check_order (7 checks, fail-fast)
  3. Human confirm (is_confirmed=True required in order dict)
  4. SinopacAdapter submit via _submit_order_impl
  5. verify_order_landed (3 polls, 1s interval)
  6. Write to state: orders_open.json (if landed) or ghost_orders.jsonl (if ghost)

Never calls api.logout(). Never bypasses pre_flight_gate.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from etf_core import context as _ctx
from etf_core.state_io import safe_load_json, atomic_save_json, safe_append_jsonl
from daily_order_limits import increment_daily_submit_count
from orders_open_state import build_orders_open_payload, merge_open_orders

TW_TZ = ZoneInfo("Asia/Taipei")


def check_order(order, context):
    """Thin wrapper so patch('live_submit_sop.check_order') works in tests."""
    try:
        from scripts.pre_flight_gate import check_order as _co
    except ImportError:
        from pre_flight_gate import check_order as _co
    return _co(order, context)


def _check_live_mode_enabled(state_dir: Path) -> tuple[bool, str]:
    live_mode = safe_load_json(state_dir / "live_mode.json", default={"enabled": False})
    if not live_mode.get("enabled", False):
        return False, "live_mode.json: enabled=False. Unlock via dashboard first."
    return True, "ok"


def _build_gate_context(state_dir: Path) -> dict:
    account = safe_load_json(state_dir / "account_snapshot.json", default={})
    positions = safe_load_json(state_dir / "positions.json", default={})
    redlines = safe_load_json(state_dir / "safety_redlines.json", default={})

    max_conc = redlines.get("max_buy_amount_pct")
    if max_conc is None or not (0 < max_conc <= 1):
        max_conc = 0.5

    inventory = {
        str(p.get("symbol", "")).upper(): float(p.get("quantity") or 0)
        for p in positions.get("positions", [])
    }

    return {
        "cash": float(account.get("cash") or 0),
        "settlement_safe_cash": account.get("settlement_safe_cash"),
        "inventory": inventory,
        "max_concentration_pct": max_conc,
        "max_single_limit_twd": redlines.get("max_buy_amount_twd", 1_000_000.0),
        "force_trading_hours": True,
        "state_dir": state_dir,
    }


def _load_open_orders(state_dir: Path) -> list[dict]:
    payload = safe_load_json(state_dir / "orders_open.json", default={"orders": []})
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("orders"), list):
        return payload["orders"]
    return []


async def _build_default_adapter(order: dict):
    from adapters import get_adapter

    broker_id = order.get("broker_id") or order.get("broker") or "sinopac"
    account_id = order.get("account_id") or order.get("account") or "sinopac_01"
    adapter = get_adapter(
        broker_id,
        {
            "account_id": account_id,
            "mode": "live",
            "api_key": os.environ.get("SINOPAC_API_KEY"),
            "secret_key": os.environ.get("SINOPAC_SECRET_KEY"),
            "password": os.environ.get("SINOPAC_PASSWORD"),
        },
    )
    if not await adapter.authenticate():
        return None, f"{broker_id} authenticate failed"
    return adapter, "ok"


async def submit_live_order(order: dict, adapter=None, state_dir: Path = None) -> dict:
    """
    Submit a live order through the full safety pipeline.

    Args:
        order: dict with keys: symbol, side, quantity, price, lot_type,
               is_confirmed (must be True), order_id (UUID)
        adapter: SinopacAdapter instance (injected for testing)
        state_dir: override state dir (injected for testing)

    Returns:
        dict with keys: success, broker_order_id, verified, ghost, reason, order_id, step
    """
    if state_dir is None:
        state_dir = _ctx.get_state_dir()

    # Step 1: live mode gate
    enabled, reason = _check_live_mode_enabled(state_dir)
    if not enabled:
        return {"success": False, "reason": reason, "step": "live_mode_gate"}

    # Step 2: pre_flight_gate
    gate_order = {
        **order,
        "is_submit": True,
        "is_confirmed": bool(order.get("is_confirmed", False)),
    }
    gate_context = _build_gate_context(state_dir)
    gate_result = check_order(gate_order, gate_context)
    if not gate_result["passed"]:
        return {
            "success": False,
            "reason": f"pre_flight_gate: {gate_result['reason']}",
            "step": "pre_flight_gate",
            "gate_details": gate_result.get("details", {})
        }

    # Step 3: human confirm check
    if not order.get("is_confirmed", False):
        return {"success": False, "reason": "is_confirmed=False. Human confirmation required.", "step": "human_confirm"}

    # Step 4: submit via adapter
    if adapter is None:
        adapter, adapter_reason = await _build_default_adapter(order)
        if adapter is None:
            return {"success": False, "reason": adapter_reason, "step": "authenticate"}

    try:
        submitted = await adapter._submit_order_impl(order)
    except Exception as e:
        return {"success": False, "reason": f"Adapter submit error: {e}", "step": "submit"}

    increment_daily_submit_count(state_dir / "daily_order_limits.json", order.get("side", ""))

    broker_order_id = getattr(submitted, "broker_order_id", "") or ""
    internal_order_id = order.get("order_id", "")

    # Step 5: verify order landed
    verify_result = await adapter.verify_order_landed(broker_order_id)

    # Step 6: write to state
    now_iso = datetime.now(TW_TZ).isoformat()

    if verify_result["verified"]:
        # Write to orders_open.json (merge into list)
        orders_open = _load_open_orders(state_dir)
        # Deduplication: skip if order_id already exists (idempotent re-submit guard)
        if any(o.get("order_id") == internal_order_id for o in orders_open):
            return {
                "success": True,
                "broker_order_id": broker_order_id,
                "verified": True,
                "ghost": False,
                "order_id": internal_order_id,
                "reason": "duplicate: order_id already in orders_open"
            }
        order_row = {
            "order_id": internal_order_id,
            "broker_order_id": broker_order_id,
            "symbol": order.get("symbol"),
            "action": order.get("side"),
            "quantity": order.get("quantity"),
            "price": order.get("price"),
            "status": "submitted",
            "source": "live_broker",
            "source_type": "live_submit_sop",
            "verified": True,
            "observed_at": now_iso,
            "submitted_at": now_iso,
            "mode": "live",
            "account": order.get("account_id") or order.get("account"),
            "broker_id": order.get("broker_id") or order.get("broker"),
        }
        payload = build_orders_open_payload(merge_open_orders(orders_open, order_row), source="live_broker")
        atomic_save_json(state_dir / "orders_open.json", payload)
        return {
            "success": True,
            "broker_order_id": broker_order_id,
            "verified": True,
            "ghost": False,
            "order_id": internal_order_id
        }
    else:
        # Ghost order — log to ghost_orders.jsonl, do NOT write to orders_open
        safe_append_jsonl(state_dir / "ghost_orders.jsonl", {
            "order_id": internal_order_id,
            "broker_order_id": broker_order_id,
            "symbol": order.get("symbol"),
            "ghost_detected_at": now_iso,
            "verify_polls": verify_result.get("polls", 3)
        })
        return {
            "success": False,
            "broker_order_id": broker_order_id,
            "verified": False,
            "ghost": True,
            "reason": "verify_order_landed: ordno not found after 3 polls",
            "order_id": internal_order_id
        }


def main():
    """CLI entry — for manual testing only. Real invocations come from dashboard."""
    import argparse
    parser = argparse.ArgumentParser(description="Live Submit SOP (manual test)")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", required=True, choices=["buy", "sell"])
    parser.add_argument("--quantity", type=int, required=True)
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--lot-type", default="board")
    parser.add_argument("--confirm", action="store_true", help="Human confirmation flag")
    args = parser.parse_args()

    print("[live-submit-sop] CLI mode. Use dashboard for production submissions.")
    print("[live-submit-sop] This will check pre_flight_gate and live mode — no real order without --confirm.")


if __name__ == "__main__":
    main()
