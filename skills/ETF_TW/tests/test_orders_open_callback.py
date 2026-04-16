from pathlib import Path
import importlib.util
import sys
import tempfile

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_callback.py")
spec = importlib.util.spec_from_file_location("orders_open_callback", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_handle_order_event_updates_orders_open_file(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        temp_path = Path(td) / "orders_open.json"
        monkeypatch.setattr(module, "ORDERS_OPEN_PATH", temp_path)

        ok = module.handle_order_event("status_update", {
            "order_id": "43e14cbd",
            "status": "submitted",
            "symbol": "00922",
            "action": "buy",
            "quantity": 50,
            "price": 27.45,
            "account": "sinopac_01",
            "broker_id": "sinopac",
        })
        assert ok is True
        payload = module.load_orders_open()
        assert len(payload["orders"]) == 1
        assert payload["orders"][0]["order_id"] == "43e14cbd"
        assert payload["orders"][0]["status"] == "submitted"


def test_handle_order_event_ignores_invalid_payload(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        temp_path = Path(td) / "orders_open.json"
        monkeypatch.setattr(module, "ORDERS_OPEN_PATH", temp_path)
        ok = module.handle_order_event("status_update", {"status": "submitted"})
        assert ok is False
