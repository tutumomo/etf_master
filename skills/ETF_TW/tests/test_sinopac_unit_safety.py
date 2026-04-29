#!/usr/bin/env python3
"""Regression tests for SinoPac share/lot conversion safety."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from adapters.base import Order
import adapters.sinopac_adapter as current
import adapters.sinopac_adapter_enhanced as legacy


class _Const:
    Buy = "Buy"
    Sell = "Sell"
    LMT = "LMT"
    MKT = "MKT"
    ROD = "ROD"
    Common = "Common"
    Odd = "Odd"
    IntradayOdd = "IntradayOdd"


class _FakeApi:
    def __init__(self):
        self.stock_account = "stock-account"
        self.Contracts = SimpleNamespace(Stocks={"0050": SimpleNamespace(reference=150.0)})
        self.orders = []

    def Order(self, **kwargs):
        self.orders.append(kwargs)
        return kwargs

    def place_order(self, *args):
        return SimpleNamespace(id="SIM-ID", order=SimpleNamespace(ordno="SIM-ORDNO"))

    def set_order_callback(self, callback):
        self.callback = callback


def _patch_constants(module):
    module.Action = _Const
    module.StockPriceType = _Const
    module.OrderType = _Const
    module.StockOrderLot = _Const


def _make_current_adapter():
    _patch_constants(current)
    adapter = current.SinopacAdapter.__new__(current.SinopacAdapter)
    adapter.authenticated = True
    adapter.api = _FakeApi()
    adapter.mode = "live"
    adapter.config = {}
    adapter.broker_id = "sinopac"
    return adapter


def _make_legacy_adapter():
    _patch_constants(legacy)
    legacy.StockOrderCond = _Const
    legacy.SinopacAdapterEnhanced.__abstractmethods__ = frozenset()
    adapter = legacy.SinopacAdapterEnhanced.__new__(legacy.SinopacAdapterEnhanced)
    adapter.authenticated = True
    adapter.api = _FakeApi()
    adapter.stock_account = "stock-account"
    adapter.order_callbacks = []
    return adapter


def test_current_adapter_sends_odd_lot_as_shares():
    current.get_trading_hours_info = lambda: {"in_after_hours": False}
    adapter = _make_current_adapter()
    order = Order(symbol="0050", action="buy", quantity=50, price=150.0)

    result = asyncio.run(current.SinopacAdapter._submit_order_impl(adapter, order))

    assert result.status == "submitted"
    assert adapter.api.orders[-1]["quantity"] == 50
    assert adapter.api.orders[-1]["order_lot"] == _Const.IntradayOdd


def test_current_adapter_uses_after_hours_odd_lot_session():
    current.get_trading_hours_info = lambda: {"in_after_hours": True}
    adapter = _make_current_adapter()
    order = Order(symbol="0050", action="sell", quantity=1, price=150.0)

    result = asyncio.run(current.SinopacAdapter._submit_order_impl(adapter, order))

    assert result.status == "submitted"
    assert adapter.api.orders[-1]["quantity"] == 1
    assert adapter.api.orders[-1]["order_lot"] == _Const.Odd


def test_current_adapter_sends_board_lot_as_lots():
    adapter = _make_current_adapter()
    order = Order(symbol="0050", action="buy", quantity=2000, price=150.0)

    result = asyncio.run(current.SinopacAdapter._submit_order_impl(adapter, order))

    assert result.status == "submitted"
    assert adapter.api.orders[-1]["quantity"] == 2
    assert adapter.api.orders[-1]["order_lot"] == _Const.Common


def test_current_adapter_rejects_mixed_lot_quantity_at_submit_impl():
    adapter = _make_current_adapter()
    order = Order(symbol="0050", action="buy", quantity=1500, price=150.0)

    result = asyncio.run(current.SinopacAdapter._submit_order_impl(adapter, order))

    assert result.status == "rejected"
    assert adapter.api.orders == []


def test_legacy_enhanced_adapter_no_longer_turns_odd_lot_into_one_board_lot():
    legacy.get_trading_hours_info = lambda: {"in_after_hours": False}
    adapter = _make_legacy_adapter()
    order = Order(symbol="0050", action="buy", quantity=50, price=150.0)

    result = asyncio.run(legacy.SinopacAdapterEnhanced.submit_order(adapter, order))

    assert result.status == "submitted"
    assert adapter.api.orders[-1]["quantity"] == 50
    assert adapter.api.orders[-1]["order_lot"] == _Const.IntradayOdd


def test_legacy_enhanced_adapter_uses_after_hours_odd_lot_session():
    legacy.get_trading_hours_info = lambda: {"in_after_hours": True}
    adapter = _make_legacy_adapter()
    order = Order(symbol="0050", action="sell", quantity=1, price=150.0)

    result = asyncio.run(legacy.SinopacAdapterEnhanced.submit_order(adapter, order))

    assert result.status == "submitted"
    assert adapter.api.orders[-1]["quantity"] == 1
    assert adapter.api.orders[-1]["order_lot"] == _Const.Odd


def test_legacy_enhanced_adapter_rejects_mixed_lot_quantity():
    adapter = _make_legacy_adapter()
    order = Order(symbol="0050", action="buy", quantity=1500, price=150.0)

    result = asyncio.run(legacy.SinopacAdapterEnhanced.submit_order(adapter, order))

    assert result.status == "rejected"
    assert adapter.api.orders == []
