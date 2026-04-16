from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sinopac_callback_normalizer.py")
spec = importlib.util.spec_from_file_location("sinopac_callback_normalizer", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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
    status = "Filled"


def test_normalize_sinopac_callback_maps_trade_objects_into_order_row():
    row = module.normalize_sinopac_callback(None, DummyTrade(), DummyStatus())
    assert row["order_id"] == "43e14cbd"
    assert row["symbol"] == "00922"
    assert row["action"] == "buy"
    assert row["quantity"] == 1000
    assert row["status"] == "filled"
    assert row["verified"] is True
