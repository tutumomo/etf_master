from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

NORMALIZER_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sinopac_callback_normalizer.py")
normalizer_spec = importlib.util.spec_from_file_location("sinopac_callback_normalizer", NORMALIZER_PATH)
normalizer_module = importlib.util.module_from_spec(normalizer_spec)
normalizer_spec.loader.exec_module(normalizer_module)

ORDERS_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/orders_open_state.py")
orders_spec = importlib.util.spec_from_file_location("orders_open_state", ORDERS_MODULE_PATH)
orders_module = importlib.util.module_from_spec(orders_spec)
orders_spec.loader.exec_module(orders_module)


class DummyContract:
    code = "00922"


class DummyInnerOrder:
    action = "Buy"
    quantity = 1
    price = 27.45


class DummyTrade:
    contract = DummyContract()
    order = DummyInnerOrder()


class DummyPartialStatus:
    order_id = "43e14cbd"
    status = "Partially_Filled"
    deal_quantity = 400
    qty = 1000


def test_normalize_sinopac_partial_fill_keeps_fill_metadata():
    row = normalizer_module.normalize_sinopac_callback(None, DummyTrade(), DummyPartialStatus())
    assert row["status"] == "partial_filled"
    assert row["filled_quantity"] == 400
    assert row["remaining_quantity"] == 600


def test_newer_timestamp_update_wins_over_older_submitted_update():
    existing = [{
        "order_id": "43e14cbd",
        "status": "submitted",
        "symbol": "00922",
        "action": "buy",
        "quantity": 1000,
        "price": 27.45,
        "updated_at": "2026-04-03T03:20:00+08:00",
    }]

    newer = {
        "order_id": "43e14cbd",
        "status": "partial_filled",
        "symbol": "00922",
        "action": "buy",
        "quantity": 400,
        "filled_quantity": 400,
        "remaining_quantity": 600,
        "price": 27.45,
        "updated_at": "2026-04-03T03:21:00+08:00",
    }

    rows = orders_module.merge_open_orders(existing, newer)
    assert len(rows) == 1
    assert rows[0]["status"] == "partial_filled"
    assert rows[0]["updated_at"] == "2026-04-03T03:21:00+08:00"


def test_stale_callback_must_not_override_newer_partial_fill_state():
    existing = [{
        "order_id": "43e14cbd",
        "status": "partial_filled",
        "symbol": "00922",
        "action": "buy",
        "quantity": 400,
        "filled_quantity": 400,
        "remaining_quantity": 600,
        "price": 27.45,
        "updated_at": "2026-04-03T03:21:00+08:00",
    }]

    stale = {
        "order_id": "43e14cbd",
        "status": "submitted",
        "symbol": "00922",
        "action": "buy",
        "quantity": 1000,
        "price": 27.45,
        "updated_at": "2026-04-03T03:19:00+08:00",
    }

    rows = orders_module.merge_open_orders(existing, stale)
    assert len(rows) == 1
    assert rows[0]["status"] == "partial_filled"
    assert rows[0]["updated_at"] == "2026-04-03T03:21:00+08:00"
    assert rows[0]["remaining_quantity"] == 600
