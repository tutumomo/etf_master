from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

BASE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/adapters/base.py")
base_spec = importlib.util.spec_from_file_location("adapter_base", BASE_MODULE_PATH)
adapter_base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(adapter_base)

LIFECYCLE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_lifecycle.py")
lifecycle_spec = importlib.util.spec_from_file_location("order_lifecycle", LIFECYCLE_MODULE_PATH)
order_lifecycle = importlib.util.module_from_spec(lifecycle_spec)
lifecycle_spec.loader.exec_module(order_lifecycle)


def test_submit_response_without_order_id_is_not_landed():
    order = adapter_base.Order(symbol="00922", action="buy", quantity=50, price=27.45, mode="live")
    order.status = "submitted"
    assert order_lifecycle.order_landed(order) is False


def test_submit_response_with_order_id_and_submitted_status_is_landed():
    order = adapter_base.Order(symbol="00922", action="buy", quantity=50, price=27.45, mode="live")
    order.status = "submitted"
    order.order_id = "43e14cbd"
    assert order_lifecycle.order_landed(order) is True


def test_pending_status_with_order_id_is_not_yet_landed_contractually():
    order = adapter_base.Order(symbol="00922", action="buy", quantity=50, price=27.45, mode="live")
    order.status = "pending"
    order.order_id = "43e14cbd"
    assert order_lifecycle.order_landed(order) is False


def test_filled_status_with_order_id_is_landed():
    order = adapter_base.Order(symbol="00922", action="buy", quantity=50, price=27.45, mode="live")
    order.status = "filled"
    order.order_id = "43e14cbd"
    assert order_lifecycle.order_landed(order) is True
