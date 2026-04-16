from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

BASE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/adapters/base.py")
base_spec = importlib.util.spec_from_file_location("adapter_base", BASE_MODULE_PATH)
adapter_base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(adapter_base)

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/submit_verification.py")
spec = importlib.util.spec_from_file_location("submit_verification", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_order(status=None, order_id=None):
    order = adapter_base.Order(symbol="00922", action="buy", quantity=50, price=27.45, mode="live")
    order.status = status
    order.order_id = order_id
    return order


def test_verification_payload_marks_verified_when_ids_match():
    submitted = make_order(status="submitted", order_id="43e14cbd")
    broker = make_order(status="submitted", order_id="43e14cbd")
    payload = module.verification_payload(submitted, broker)
    assert payload["verified"] is True
    assert payload["landed_by_submit"] is True
    assert payload["landed_by_broker"] is True


def test_verification_payload_marks_unverified_when_broker_missing():
    submitted = make_order(status="submitted", order_id="43e14cbd")
    payload = module.verification_payload(submitted, None)
    assert payload["verified"] is False
    assert payload["landed_by_submit"] is True
    assert payload["landed_by_broker"] is False


def test_verification_payload_marks_unverified_when_ids_do_not_match():
    submitted = make_order(status="submitted", order_id="43e14cbd")
    broker = make_order(status="submitted", order_id="DIFFERENT")
    payload = module.verification_payload(submitted, broker)
    assert payload["verified"] is False
