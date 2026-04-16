import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW")
sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

from scripts.adapters import sinopac_adapter as adapter_module
import orders_open_callback as callback_module


class DummyContract:
    code = "00922"


class DummyInnerOrder:
    action = "Buy"
    quantity = 1
    price = 27.45


class DummyTrade:
    contract = DummyContract()
    order = DummyInnerOrder()


class DummyStatus:
    order_id = "43e14cbd"
    status = "Submitted"


def test_sinopac_callback_bridge_smoke_updates_orders_open(monkeypatch):
    adapter = adapter_module.SinopacAdapter('sinopac', {'mode': 'live'})
    adapter.order_callbacks = []
    adapter.register_default_state_callback()

    with tempfile.TemporaryDirectory() as td:
        temp_path = Path(td) / "orders_open.json"
        monkeypatch.setattr(callback_module, "ORDERS_OPEN_PATH", temp_path)

        for cb in adapter.order_callbacks:
            if getattr(cb, "__name__", "") == "_callback_bridge":
                cb(None, DummyTrade(), DummyStatus())

        payload = callback_module.load_orders_open()
        assert len(payload["orders"]) == 1
        row = payload["orders"][0]
        assert row["order_id"] == "43e14cbd"
        assert row["symbol"] == "00922"
        assert row["status"] == "submitted"
        assert row["verified"] is True
