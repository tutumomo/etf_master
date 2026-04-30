from pathlib import Path
import importlib.util
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/poll_order_status.py")
spec = importlib.util.spec_from_file_location("poll_order_status", MODULE_PATH)
poll_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poll_module)


def test_partial_fill_polling_row_is_recordable_as_fill_fact():
    row = poll_module.build_polling_order_row(
        order_id="pf-001",
        symbol="00922",
        action="buy",
        quantity=1000,
        price=27.45,
        status="partial_filled",
    )
    assert row["status"] == "partial_filled"
    assert row["source_type"] == "broker_polling"


def test_polling_partial_fill_updates_fills_ledger(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        fills_path = Path(td) / "fills_ledger.json"
        monkeypatch.setattr(poll_module, "FILLS_LEDGER_PATH", fills_path)
        poll_module.save_fills_ledger([
            {
                "order_id": "pf-001",
                "symbol": "00922",
                "filled_quantity": 300,
                "price": 27.45,
                "status": "partial_filled",
                "source_type": "broker_polling",
                "observed_at": "2026-04-03T09:01:09+08:00",
            }
        ])
        payload = poll_module.load_fills_ledger()
        assert len(payload["fills"]) == 1
        assert payload["fills"][0]["order_id"] == "pf-001"


def test_polling_filled_order_row_can_update_fills_ledger(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        fills_path = Path(td) / "fills_ledger.json"
        monkeypatch.setattr(poll_module, "FILLS_LEDGER_PATH", fills_path)
        order_row = poll_module.build_polling_order_row(
            order_id="fd-001",
            symbol="006208",
            action="sell",
            quantity=8,
            price=211.5,
            status="filled",
        )
        poll_module.save_fills_ledger(
            poll_module.merge_fill_facts([], order_row)
        )
        payload = poll_module.load_fills_ledger()
        assert len(payload["fills"]) == 1
        assert payload["fills"][0]["order_id"] == "fd-001"
        assert payload["fills"][0]["status"] == "filled"
        assert payload["fills"][0]["filled_quantity"] == 8
