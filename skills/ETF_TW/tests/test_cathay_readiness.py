import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

import pytest
from adapters.base import Order
from adapters.cathay_adapter import create_cathay_adapter, build_cathay_readiness
import broker_readiness


def test_cathay_readiness_requires_official_integration_fields():
    readiness = build_cathay_readiness({"account_id": "test", "password": "test"})
    assert readiness["ready"] is False
    assert readiness["live_enabled"] is False
    assert "official_api_spec_path" in readiness["missing"]
    assert "unit_mapping_verified" in readiness["missing"]


@pytest.mark.asyncio
async def test_cathay_authenticate_does_not_simulate_success():
    adapter = create_cathay_adapter({"account_id": "test", "password": "test"})
    assert await adapter.authenticate() is False
    assert adapter.authenticated is False


@pytest.mark.asyncio
async def test_cathay_submit_rejects_without_fake_fill():
    adapter = create_cathay_adapter({"account_id": "test"})
    order = Order(symbol="0050", action="buy", quantity=1, price=100.0)
    order.is_confirmed = True
    result = await adapter._submit_order_impl(order)
    assert result.status == "rejected"
    assert result.filled_quantity == 0
    assert "not live-ready" in result.error


@pytest.mark.asyncio
async def test_cathay_preview_limit_order_is_estimate_only():
    adapter = create_cathay_adapter({})
    order = Order(symbol="0050", action="buy", quantity=10, price=100.0)
    preview = await adapter.preview_order(order)
    assert preview.status == "preview"
    assert preview._truth_level == "ESTIMATE"


def test_broker_readiness_marks_cathay_not_live_ready():
    registry = {
        "brokers": {
            "cathay": {
                "name": "國泰綜合證券",
                "api_available": False,
                "supports_sandbox": False,
                "supports_live": False,
            }
        }
    }
    report = broker_readiness.build_readiness_report(registry=registry)
    row = report["brokers"][0]
    assert row["broker_id"] == "cathay"
    assert row["live_ready"] is False
    assert "official_api_spec_path" in row["missing"]
