from pathlib import Path
import importlib.util
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW")
sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_callback.py")
spec = importlib.util.spec_from_file_location("orders_open_callback", MODULE_PATH)
callback_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(callback_module)


def test_partial_fill_event_updates_fills_ledger(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        orders_path = Path(td) / "orders_open.json"
        fills_path = Path(td) / "fills_ledger.json"
        monkeypatch.setattr(callback_module, "ORDERS_OPEN_PATH", orders_path)
        monkeypatch.setattr(callback_module, "FILLS_LEDGER_PATH", fills_path)

        callback_module.handle_order_event("status_update", {
            "order_id": "pf-001",
            "symbol": "00922",
            "action": "buy",
            "status": "partial_filled",
            "filled_quantity": 300,
            "remaining_quantity": 700,
            "price": 27.45,
        })

        fills_payload = callback_module.load_fills_ledger()
        assert len(fills_payload["fills"]) == 1
        assert fills_payload["fills"][0]["order_id"] == "pf-001"
        assert fills_payload["fills"][0]["filled_quantity"] == 300


def test_filled_event_updates_fills_ledger(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        fills_path = Path(td) / "fills_ledger.json"
        orders_path = Path(td) / "orders_open.json"
        monkeypatch.setattr(callback_module, "FILLS_LEDGER_PATH", fills_path)
        monkeypatch.setattr(callback_module, "ORDERS_OPEN_PATH", orders_path)
        ok = callback_module.handle_order_event("order_filled", {
            "order_id": "fd-001",
            "symbol": "006208",
            "action": "sell",
            "quantity": 8,
            "price": 211.5,
        })
        assert ok is True
        fills_payload = callback_module.load_fills_ledger()
        assert len(fills_payload["fills"]) == 1
        assert fills_payload["fills"][0]["order_id"] == "fd-001"
        assert fills_payload["fills"][0]["status"] == "filled"
        assert fills_payload["fills"][0]["filled_quantity"] == 8
