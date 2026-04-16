import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW")

from scripts.adapters import sinopac_adapter as module


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


def test_callback_bridge_sends_normalized_payload_to_state_handler(monkeypatch):
    adapter = module.SinopacAdapter('sinopac', {'mode': 'live'})
    captured = {}

    def fake_handle(event_type, payload):
        captured['event_type'] = event_type
        captured['payload'] = payload
        return True

    monkeypatch.setattr(module, 'handle_order_event', fake_handle)
    adapter._callback_bridge(None, DummyTrade(), DummyStatus())
    assert captured['event_type'] == 'status_update'
    assert captured['payload']['order_id'] == '43e14cbd'
    assert captured['payload']['status'] == 'filled'
    assert captured['payload']['verified'] is True
