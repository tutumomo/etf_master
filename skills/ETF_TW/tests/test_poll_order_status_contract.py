from pathlib import Path
import importlib.util

LIFECYCLE_MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/order_lifecycle.py")
lifecycle_spec = importlib.util.spec_from_file_location("order_lifecycle", LIFECYCLE_MODULE_PATH)
order_lifecycle = importlib.util.module_from_spec(lifecycle_spec)
lifecycle_spec.loader.exec_module(order_lifecycle)


def test_polling_contract_treats_failed_as_terminal_rejected():
    class Trade:
        status = "failed"
        order_id = "abc"

    trade = Trade()
    assert order_lifecycle.normalize_order_status(trade.status) == "rejected"
    assert order_lifecycle.order_terminal(trade) is True


def test_polling_contract_keeps_submitted_non_terminal():
    class Trade:
        status = "submitted"
        order_id = "abc"

    trade = Trade()
    assert order_lifecycle.normalize_order_status(trade.status) == "submitted"
    assert order_lifecycle.order_terminal(trade) is False
