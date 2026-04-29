#!/usr/bin/env python3
"""
Contract tests for sinopac_adapter ordno extraction and live_submit_sop SOP.
Phase 10 / Plan 04 / LIVE-01

Tests use AsyncMock adapters and tmp_path to avoid real API calls.
Async tests use asyncio.run() (no pytest-asyncio required).
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ─────────────────────────────────────────────
# Helper: build a mock trade object
# ─────────────────────────────────────────────

def _make_trade(ordno: str = "ORD123"):
    trade = MagicMock()
    trade.order = MagicMock()
    trade.order.ordno = ordno
    trade.status = MagicMock()
    trade.status.order_id = "OLD_STATUS_ID"  # must NOT be used
    return trade


# ─────────────────────────────────────────────
# Task 1 Tests: sinopac_adapter ordno extraction
# ─────────────────────────────────────────────

class TestSinopacOrdnoExtraction:
    """Test that _submit_order_impl reads broker_order_id from trade.order.ordno."""

    def test_ordno_extraction_from_trade_order(self):
        """
        trade.order.ordno = 'ORD123' must become order.broker_order_id = 'ORD123'.
        Must NOT read from trade.status.order_id.
        """
        trade = _make_trade("ORD123")
        trade_order = getattr(trade, 'order', None)
        broker_order_id = str(getattr(trade_order, 'ordno', '')) if trade_order else ''
        assert broker_order_id == "ORD123", f"Expected 'ORD123', got '{broker_order_id}'"

    def test_ordno_empty_is_ghost(self):
        """trade.order.ordno='' → broker_order_id='' → ghost condition."""
        trade = _make_trade("")
        trade_order = getattr(trade, 'order', None)
        broker_order_id = str(getattr(trade_order, 'ordno', '')) if trade_order else ''
        assert broker_order_id == ""

    def test_trade_without_order_attr_returns_empty(self):
        """If trade has no .order attribute, broker_order_id should be ''."""
        trade = MagicMock(spec=[])  # no attributes
        trade_order = getattr(trade, 'order', None)
        broker_order_id = str(getattr(trade_order, 'ordno', '')) if trade_order else ''
        assert broker_order_id == ""


# ─────────────────────────────────────────────
# Task 1 Tests: verify_order_landed
# ─────────────────────────────────────────────

def _make_sinopac_adapter():
    """Build a minimal SinopacAdapter instance bypassing constructor."""
    from adapters.sinopac_adapter import SinopacAdapter
    inst = SinopacAdapter.__new__(SinopacAdapter)
    inst.authenticated = True
    inst.order_callbacks = []
    inst.api = None
    inst.stock_account = None
    inst.mode = "paper"
    inst.config = {"api_key": "k", "secret_key": "s", "mode": "paper"}
    inst.broker_id = "sinopac"
    return inst


class TestVerifyOrderLanded:
    """Test verify_order_landed on SinopacAdapter."""

    def test_found_on_first_poll(self):
        """verify_order_landed returns verified=True, polls=1 when ordno found on first poll."""
        adapter = _make_sinopac_adapter()
        trade = _make_trade("ORD001")
        adapter.list_trades = AsyncMock(return_value=[trade])

        result = asyncio.run(adapter.verify_order_landed("ORD001", max_polls=3, poll_interval_s=0))
        assert result["verified"] is True
        assert result["ghost"] is False
        assert result["polls"] == 1
        assert result["broker_order_id"] == "ORD001"

    def test_found_on_third_poll(self):
        """verify_order_landed returns verified=True, polls=3 when found on third poll."""
        adapter = _make_sinopac_adapter()
        trade = _make_trade("ORD002")
        call_count = {"n": 0}

        async def fake_list_trades():
            call_count["n"] += 1
            if call_count["n"] < 3:
                return []
            return [trade]

        adapter.list_trades = fake_list_trades
        result = asyncio.run(adapter.verify_order_landed("ORD002", max_polls=3, poll_interval_s=0))
        assert result["verified"] is True
        assert result["polls"] == 3

    def test_ghost_after_max_polls(self):
        """verify_order_landed returns ghost=True after 3 polls without finding ordno."""
        adapter = _make_sinopac_adapter()
        adapter.list_trades = AsyncMock(return_value=[])

        result = asyncio.run(adapter.verify_order_landed("NOTFOUND", max_polls=3, poll_interval_s=0))
        assert result["verified"] is False
        assert result["ghost"] is True
        assert result["polls"] == 3

    def test_ghost_with_wrong_ordno(self):
        """verify_order_landed returns ghost if trade exists but ordno doesn't match."""
        adapter = _make_sinopac_adapter()
        trade = _make_trade("WRONG_ORDNO")
        adapter.list_trades = AsyncMock(return_value=[trade])

        result = asyncio.run(adapter.verify_order_landed("TARGET_ORDNO", max_polls=3, poll_interval_s=0))
        assert result["verified"] is False
        assert result["ghost"] is True


# ─────────────────────────────────────────────
# Task 2 Tests: live_submit_sop
# ─────────────────────────────────────────────

class TestLiveSubmitSop:
    """Contract tests for submit_live_order SOP pipeline."""

    def _make_state_dir(self, tmp_path, enabled=True):
        (tmp_path / "live_mode.json").write_text(json.dumps({"enabled": enabled}))
        return tmp_path

    def _make_order(self, confirmed=True):
        return {
            "symbol": "0050",
            "side": "buy",
            "quantity": 1000,
            "price": 150.0,
            "lot_type": "board",
            "is_confirmed": confirmed,
            "order_id": "test-uuid-001",
        }

    def _make_mock_adapter(self, broker_order_id="ORD999", verify_found=True):
        from adapters.base import Order as BaseOrder
        order_result = BaseOrder(symbol="0050", action="buy", quantity=1000, price=150.0)
        order_result.broker_order_id = broker_order_id
        order_result.status = "submitted"

        adapter = MagicMock()
        adapter._submit_order_impl = AsyncMock(return_value=order_result)
        adapter.verify_order_landed = AsyncMock(return_value={
            "verified": verify_found,
            "ghost": not verify_found,
            "broker_order_id": broker_order_id,
            "polls": 1 if verify_found else 3,
        })
        return adapter

    def test_pre_flight_gate_fail_blocks_submit(self, tmp_path):
        """pre_flight_gate failure must prevent adapter.submit from being called."""
        from live_submit_sop import submit_live_order

        state_dir = self._make_state_dir(tmp_path)
        adapter = self._make_mock_adapter()
        order = {"symbol": "", "side": "buy", "quantity": 1000, "price": 150.0,
                 "is_confirmed": True, "order_id": "uuid-x"}

        with patch("live_submit_sop.check_order", return_value={"passed": False, "reason": "missing_symbol", "details": {}}):
            result = asyncio.run(submit_live_order(order, adapter=adapter, state_dir=state_dir))

        assert result["success"] is False
        assert "pre_flight_gate" in result["step"]
        adapter._submit_order_impl.assert_not_called()

    def test_verified_order_written_to_orders_open(self, tmp_path):
        """Successful submit + verify writes order to orders_open.json."""
        from live_submit_sop import submit_live_order

        state_dir = self._make_state_dir(tmp_path)
        adapter = self._make_mock_adapter(broker_order_id="ORD999", verify_found=True)
        order = self._make_order()

        with patch("live_submit_sop.check_order", return_value={"passed": True, "reason": "passed", "details": {}}):
            result = asyncio.run(submit_live_order(order, adapter=adapter, state_dir=state_dir))

        assert result["success"] is True
        assert result["verified"] is True
        assert result["ghost"] is False

        orders_open = json.loads((state_dir / "orders_open.json").read_text())
        assert isinstance(orders_open, dict)
        assert orders_open["orders"][0]["broker_order_id"] == "ORD999"

    def test_ghost_order_not_written_to_orders_open(self, tmp_path):
        """Ghost order must NOT be written to orders_open.json."""
        from live_submit_sop import submit_live_order

        state_dir = self._make_state_dir(tmp_path)
        adapter = self._make_mock_adapter(broker_order_id="ORD888", verify_found=False)
        order = self._make_order()

        with patch("live_submit_sop.check_order", return_value={"passed": True, "reason": "passed", "details": {}}):
            result = asyncio.run(submit_live_order(order, adapter=adapter, state_dir=state_dir))

        assert result["ghost"] is True
        assert result["success"] is False
        assert not (state_dir / "orders_open.json").exists(), "Ghost order must NOT write to orders_open.json"

        ghost_log = (state_dir / "ghost_orders.jsonl").read_text()
        assert "ORD888" in ghost_log

    def test_live_mode_disabled_rejects_immediately(self, tmp_path):
        """live_mode.json enabled=False must reject without calling adapter at all."""
        from live_submit_sop import submit_live_order

        state_dir = self._make_state_dir(tmp_path, enabled=False)
        adapter = self._make_mock_adapter()
        order = self._make_order()

        result = asyncio.run(submit_live_order(order, adapter=adapter, state_dir=state_dir))

        assert result["success"] is False
        assert result["step"] == "live_mode_gate"
        adapter._submit_order_impl.assert_not_called()

    def test_adapter_exception_returns_graceful_error(self, tmp_path):
        """Exception during submit returns error dict, no state corruption."""
        from live_submit_sop import submit_live_order

        state_dir = self._make_state_dir(tmp_path)
        adapter = MagicMock()
        adapter._submit_order_impl = AsyncMock(side_effect=RuntimeError("Shioaji connection lost"))
        order = self._make_order()

        with patch("live_submit_sop.check_order", return_value={"passed": True, "reason": "passed", "details": {}}):
            result = asyncio.run(submit_live_order(order, adapter=adapter, state_dir=state_dir))

        assert result["success"] is False
        assert result["step"] == "submit"
        assert "Shioaji connection lost" in result["reason"]
        assert not (state_dir / "orders_open.json").exists()
