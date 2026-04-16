from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

BRIDGE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_event_bridge.py")
bridge_spec = importlib.util.spec_from_file_location("order_event_bridge", BRIDGE_PATH)
bridge_module = importlib.util.module_from_spec(bridge_spec)
bridge_spec.loader.exec_module(bridge_module)

NORMALIZER_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sinopac_callback_normalizer.py")
normalizer_spec = importlib.util.spec_from_file_location("sinopac_callback_normalizer", NORMALIZER_PATH)
normalizer_module = importlib.util.module_from_spec(normalizer_spec)
normalizer_spec.loader.exec_module(normalizer_module)


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


def test_order_event_bridge_sets_source_metadata():
    row = bridge_module.event_payload_to_order_row("order_submitted", {
        "order_id": "43e14cbd",
        "symbol": "00922",
        "action": "buy",
        "quantity": 50,
        "price": 27.45,
    })
    assert row["source_type"] == "broker_callback"
    assert "observed_at" in row
    assert row["raw_status"] == "submitted"


def test_sinopac_normalizer_sets_source_metadata():
    row = normalizer_module.normalize_sinopac_callback(None, DummyTrade(), DummyStatus())
    assert row["source_type"] == "broker_callback"
    assert "observed_at" in row
    assert row["raw_status"] == "submitted"
