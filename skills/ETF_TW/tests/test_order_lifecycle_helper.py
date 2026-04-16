from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_lifecycle.py")
spec = importlib.util.spec_from_file_location("order_lifecycle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DummyOrder:
    def __init__(self, status=None, order_id=None):
        self.status = status
        self.order_id = order_id


def test_normalize_order_status_maps_failed_to_rejected():
    assert module.normalize_order_status("failed") == "rejected"
    assert module.normalize_order_status("error") == "rejected"


def test_order_landed_requires_order_id_and_landed_status():
    assert module.order_landed(DummyOrder(status="submitted", order_id="abc")) is True
    assert module.order_landed(DummyOrder(status="filled", order_id="abc")) is True
    assert module.order_landed(DummyOrder(status="pending", order_id="abc")) is False
    assert module.order_landed(DummyOrder(status="submitted", order_id=None)) is False


def test_order_terminal_only_for_terminal_statuses():
    assert module.order_terminal(DummyOrder(status="filled", order_id="abc")) is True
    assert module.order_terminal(DummyOrder(status="cancelled", order_id="abc")) is True
    assert module.order_terminal(DummyOrder(status="rejected", order_id="abc")) is True
    assert module.order_terminal(DummyOrder(status="submitted", order_id="abc")) is False
