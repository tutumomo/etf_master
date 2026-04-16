import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW")

from scripts.adapters import sinopac_adapter as module


def test_register_default_state_callback_is_idempotent():
    adapter = module.SinopacAdapter('sinopac', {'mode': 'live'})
    adapter.order_callbacks = []
    adapter.register_default_state_callback()
    adapter.register_default_state_callback()
    assert adapter._default_state_callback in adapter.order_callbacks
    assert adapter._callback_bridge in adapter.order_callbacks
    assert adapter.order_callbacks.count(adapter._default_state_callback) == 1
    assert adapter.order_callbacks.count(adapter._callback_bridge) == 1
