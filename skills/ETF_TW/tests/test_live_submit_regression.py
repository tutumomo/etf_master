#!/usr/bin/env python3
"""
Live Submit Regression Tests — LIVE-03
6 scenario tests covering the full live submit cycle.

Scenarios:
  1. Happy path: submit → verify → orders_open.json written
  2. Ghost order: submit → verify fails → ghost_orders.jsonl written, orders_open NOT written
  3. pre_flight_gate blocks: gate fails → adapter never called
  4. Adapter exception: RuntimeError → graceful error, state untouched
  5. Double-submit prevention: same order_id twice → only one entry in orders_open.json
  6. Live mode locked: live_mode.json absent/disabled → rejected before gate

All tests use:
  - tmp_path for state isolation (NEVER reads from instances/etf_master/state/)
  - AsyncMock for adapter calls (NO real shioaji SDK)
  - asyncio.run() for coroutine execution
"""

import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from live_submit_sop import submit_live_order
from adapters.base import Order


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_live_mode_json(tmp_path: Path, enabled: bool = True) -> None:
    data = {
        "enabled": enabled,
        "unlocked_at": "2026-04-17T09:00:00+08:00",
        "unlocked_by": "test",
    }
    (tmp_path / "live_mode.json").write_text(json.dumps(data))


def make_valid_order(order_id: str = "test-001") -> dict:
    return {
        "symbol": "0050",
        "side": "buy",
        "quantity": 1000,
        "price": 150.0,
        "lot_type": "board",
        "is_confirmed": True,
        "is_submit": True,
        "order_id": order_id,
    }


def make_mock_adapter(
    broker_order_id: str = "ORD123",
    verify_result: dict = None,
) -> MagicMock:
    adapter = MagicMock()
    submitted_order = MagicMock()
    submitted_order.broker_order_id = broker_order_id
    submitted_order.status = "submitted"
    adapter._submit_order_impl = AsyncMock(return_value=submitted_order)
    if verify_result is None:
        verify_result = {
            "verified": True,
            "ghost": False,
            "broker_order_id": broker_order_id,
            "polls": 1,
        }
    adapter.verify_order_landed = AsyncMock(return_value=verify_result)
    return adapter


# ---------------------------------------------------------------------------
# Autouse fixture: bypass trading hours in all tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def bypass_trading_hours(monkeypatch):
    """Bypass pre_flight_gate trading hours check for all tests."""
    monkeypatch.setattr(
        "live_submit_sop.check_order",
        lambda order, ctx: {"passed": True, "reason": "passed", "details": {}},
    )


def test_live_submit_gate_receives_redlines_and_settlement_safe_cash(tmp_path, monkeypatch):
    """Live submit SOP must pass account/redline context into pre_flight_gate."""
    make_live_mode_json(tmp_path)
    (tmp_path / "account_snapshot.json").write_text(json.dumps({
        "cash": 100000,
        "settlement_safe_cash": 0,
    }))
    (tmp_path / "positions.json").write_text(json.dumps({"positions": []}))
    (tmp_path / "safety_redlines.json").write_text(json.dumps({
        "max_buy_amount_pct": 0.5,
        "max_buy_amount_twd": 500000,
    }))
    captured = {}

    def fake_check_order(order, ctx):
        captured["order"] = order
        captured["ctx"] = ctx
        return {
            "passed": False,
            "reason": "exceeds_sizing_limit",
            "details": {"sizing_base": "settlement_safe_cash"},
        }

    monkeypatch.setattr("live_submit_sop.check_order", fake_check_order)
    adapter = make_mock_adapter("ORDCTX")

    result = asyncio.run(
        submit_live_order(make_valid_order("ctx-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["step"] == "pre_flight_gate"
    assert captured["order"]["is_submit"] is True
    assert captured["order"]["is_confirmed"] is True
    assert captured["ctx"]["settlement_safe_cash"] == 0
    assert captured["ctx"]["max_concentration_pct"] == 0.5
    assert captured["ctx"]["max_single_limit_twd"] == 500000
    adapter._submit_order_impl.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 1: Happy path
# ---------------------------------------------------------------------------

def test_happy_path_order_written_to_orders_open(tmp_path):
    """Happy path: submit succeeds, verify confirms order → orders_open.json written."""
    make_live_mode_json(tmp_path)
    adapter = make_mock_adapter("ORD001")

    result = asyncio.run(
        submit_live_order(make_valid_order("happy-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is True
    assert result["verified"] is True
    assert result["ghost"] is False

    orders_open_path = tmp_path / "orders_open.json"
    assert orders_open_path.exists(), "orders_open.json must be created on success"
    orders_open = json.loads(orders_open_path.read_text())
    assert any(
        o.get("broker_order_id") == "ORD001" for o in orders_open
    ), "ORD001 must appear in orders_open.json"


# ---------------------------------------------------------------------------
# Scenario 2: Ghost order
# ---------------------------------------------------------------------------

def test_ghost_order_logged_not_in_orders_open(tmp_path):
    """Ghost: submit returns ordno but verify finds nothing → ghost_orders.jsonl written, orders_open NOT written."""
    make_live_mode_json(tmp_path)
    ghost_verify = {
        "verified": False,
        "ghost": True,
        "broker_order_id": "ORD002",
        "polls": 3,
    }
    adapter = make_mock_adapter("ORD002", verify_result=ghost_verify)

    result = asyncio.run(
        submit_live_order(make_valid_order("ghost-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["ghost"] is True

    ghost_log = tmp_path / "ghost_orders.jsonl"
    assert ghost_log.exists(), "ghost_orders.jsonl must be created for ghost orders"
    last_record = json.loads(ghost_log.read_text().strip().splitlines()[-1])
    assert last_record["broker_order_id"] == "ORD002"

    # orders_open.json must NOT contain this broker_order_id
    orders_open_path = tmp_path / "orders_open.json"
    if orders_open_path.exists():
        orders_open = json.loads(orders_open_path.read_text())
        assert not any(
            o.get("broker_order_id") == "ORD002" for o in orders_open
        ), "Ghost order must NOT appear in orders_open.json"


# ---------------------------------------------------------------------------
# Scenario 3: pre_flight_gate blocks
# ---------------------------------------------------------------------------

def test_preflight_gate_blocks_submit(tmp_path, monkeypatch):
    """Gate block: pre_flight_gate returns passed=False → adapter._submit_order_impl never called."""
    make_live_mode_json(tmp_path)
    monkeypatch.setattr(
        "live_submit_sop.check_order",
        lambda order, ctx: {
            "passed": False,
            "reason": "outside_trading_hours",
            "details": {},
        },
    )
    adapter = make_mock_adapter()

    result = asyncio.run(
        submit_live_order(make_valid_order(), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["step"] == "pre_flight_gate"
    adapter._submit_order_impl.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 4: Adapter exception
# ---------------------------------------------------------------------------

def test_adapter_exception_graceful_error(tmp_path):
    """Exception: adapter raises RuntimeError → graceful error dict, state files untouched."""
    make_live_mode_json(tmp_path)
    adapter = MagicMock()
    adapter._submit_order_impl = AsyncMock(
        side_effect=RuntimeError("shioaji connection refused")
    )

    result = asyncio.run(
        submit_live_order(make_valid_order(), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["step"] == "submit"
    assert "shioaji connection refused" in result["reason"]

    assert not (tmp_path / "orders_open.json").exists(), (
        "orders_open.json must NOT be created after adapter exception"
    )


# ---------------------------------------------------------------------------
# Scenario 5: Double-submit prevention
# ---------------------------------------------------------------------------

def test_double_submit_no_duplicate_in_orders_open(tmp_path):
    """Idempotency: same order_id submitted twice → only one entry in orders_open.json."""
    make_live_mode_json(tmp_path)
    adapter = make_mock_adapter("ORD003")
    order = make_valid_order("dup-001")

    asyncio.run(submit_live_order(order, adapter=adapter, state_dir=tmp_path))
    asyncio.run(submit_live_order(order, adapter=adapter, state_dir=tmp_path))

    orders_open_path = tmp_path / "orders_open.json"
    assert orders_open_path.exists()
    orders_open = json.loads(orders_open_path.read_text())
    entries = [o for o in orders_open if o.get("order_id") == "dup-001"]
    assert len(entries) <= 1, (
        f"Duplicate order detected: {len(entries)} entries for order_id=dup-001. "
        "live_submit_sop must deduplicate by order_id before appending."
    )


# ---------------------------------------------------------------------------
# Scenario 6: Live mode locked
# ---------------------------------------------------------------------------

def test_live_mode_locked_rejects_before_gate(tmp_path):
    """Live mode lock: live_mode.json absent or enabled=False → rejected at live_mode_gate."""
    # No live_mode.json written → defaults to disabled
    adapter = make_mock_adapter()

    result = asyncio.run(
        submit_live_order(make_valid_order(), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["step"] == "live_mode_gate"
    adapter._submit_order_impl.assert_not_called()
    adapter.verify_order_landed.assert_not_called()


def test_live_mode_explicitly_disabled_rejects(tmp_path):
    """Live mode lock: live_mode.json with enabled=False → rejected at live_mode_gate."""
    make_live_mode_json(tmp_path, enabled=False)
    adapter = make_mock_adapter()

    result = asyncio.run(
        submit_live_order(make_valid_order(), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert result["step"] == "live_mode_gate"
    adapter._submit_order_impl.assert_not_called()


def test_successful_buy_submit_increments_daily_buy_quota(tmp_path):
    """Live submit counts once the broker submit succeeds, regardless of later fill state."""
    make_live_mode_json(tmp_path)
    adapter = make_mock_adapter("ORD004")

    result = asyncio.run(
        submit_live_order(make_valid_order("quota-buy-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is True
    daily_limits = json.loads((tmp_path / "daily_order_limits.json").read_text())
    assert daily_limits["buy_submit_count"] == 1
    assert daily_limits["sell_submit_count"] == 0


def test_ghost_submit_still_counts_daily_buy_quota(tmp_path):
    """Ghost orders still consume submit quota because broker submit already happened."""
    make_live_mode_json(tmp_path)
    ghost_verify = {
        "verified": False,
        "ghost": True,
        "broker_order_id": "ORD005",
        "polls": 3,
    }
    adapter = make_mock_adapter("ORD005", verify_result=ghost_verify)

    result = asyncio.run(
        submit_live_order(make_valid_order("quota-buy-ghost-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["ghost"] is True
    daily_limits = json.loads((tmp_path / "daily_order_limits.json").read_text())
    assert daily_limits["buy_submit_count"] == 1


def test_gate_block_does_not_increment_daily_quota(tmp_path, monkeypatch):
    """Pre-flight rejection must not consume submit quota."""
    make_live_mode_json(tmp_path)
    monkeypatch.setattr(
        "live_submit_sop.check_order",
        lambda order, ctx: {"passed": False, "reason": "quota_blocked", "details": {}},
    )
    adapter = make_mock_adapter()

    result = asyncio.run(
        submit_live_order(make_valid_order("quota-block-001"), adapter=adapter, state_dir=tmp_path)
    )

    assert result["success"] is False
    assert not (tmp_path / "daily_order_limits.json").exists()
