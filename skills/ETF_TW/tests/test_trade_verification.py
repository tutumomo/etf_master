import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from scripts.submit_verification import verify_order_landing, verification_payload
from scripts.truth_level import LEVEL_1_LIVE, LEVEL_2_VERIFYING

def test_list_trades_empty_response():
    # TEST-02: list_trades 空回應不反推交易結果
    mock_adapter = MagicMock()
    mock_adapter.list_trades = AsyncMock(return_value=[])

    result = asyncio.run(verify_order_landing(mock_adapter, "order_123", timeout=1))
    
    assert result["verified"] is False
    assert result["_truth_level"] == LEVEL_2_VERIFYING
    assert "未落地" in result["message"] or "待確認" in result["message"]

def test_submit_success_but_not_landed():
    # TEST-03: 委託 submit 成功未落地時不報為已成交
    
    class MockOrder:
        def __init__(self, order_id, status):
            self.order_id = order_id
            self.status = status

    submitted_order = MockOrder("order_123", "submitted")
    broker_order = None # 未落地
    
    result = verification_payload(submitted_order, broker_order)
    
    assert result["landed_by_broker"] is False
    assert result["verified"] is False
    assert result["_truth_level"] == LEVEL_2_VERIFYING
    assert result["broker_status"] is None
