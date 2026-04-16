#!/usr/bin/env python3
"""
Test script for Phase 4 - Multi-broker architecture.

Tests:
1. Load broker registry
2. Load account configuration
3. Get adapter for different brokers
4. Test paper trading adapter
"""

import asyncio
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from account_manager import get_account_manager
from adapters.base import get_adapter


async def test_broker_registry():
    """Test 1: Load and display broker registry."""
    print("=" * 72)
    print("測試 1：券商註冊表")
    print("=" * 72)
    
    manager = get_account_manager()
    brokers = manager.list_brokers()
    
    print(f"已載入 {len(brokers)} 個券商：")
    for broker in brokers:
        print(f"  - {broker['broker_id']}: {broker.get('name', broker.get('name_en', 'Unknown'))}")
        print(f"    類型：{broker['type']}")
        print(f"    支援模式：paper={broker.get('supports_paper', False)}, "
              f"sandbox={broker.get('supports_sandbox', False)}, "
              f"live={broker.get('supports_live', False)}")
    print()


async def test_account_config():
    """Test 2: Load account configuration."""
    print("=" * 72)
    print("測試 2：帳戶配置")
    print("=" * 72)
    
    manager = get_account_manager()
    accounts = manager.list_accounts()
    
    print(f"已配置 {len(accounts)} 個帳戶：")
    for acc in accounts:
        print(f"  - 別名：{acc['alias']}")
        print(f"    券商：{acc['broker_id']}")
        print(f"    帳號：{acc['account_id']}")
        print(f"    模式：{acc['mode']}")
    print()


async def test_adapter_instantiation():
    """Test 3: Get adapters for different brokers."""
    print("=" * 72)
    print("測試 3：適配器實例化")
    print("=" * 72)
    
    manager = get_account_manager()
    accounts = manager.list_accounts()
    
    for acc in accounts:
        try:
            adapter = manager.get_adapter(acc['alias'])
            print(f"  ✓ {acc['alias']}: {type(adapter).__name__}")
        except Exception as e:
            print(f"  ✗ {acc['alias']}: {e}")
    print()


async def test_paper_trading():
    """Test 4: Test paper trading adapter."""
    print("=" * 72)
    print("測試 4：模擬交易（Paper Trading）")
    print("=" * 72)
    
    try:
        manager = get_account_manager()
        adapter = manager.get_adapter('default')
        
        # Authenticate
        auth_result = await adapter.authenticate()
        print(f"認證：{'成功' if auth_result else '失敗'}")
        
        if not auth_result:
            return
        
        # Get balance
        balance = await adapter.get_account_balance('paper_001')
        print(f"帳戶餘額：NT$ {balance.cash_available:,.0f}")
        print(f"可用餘額：NT$ {balance.buying_power:,.0f}")
        
        # Preview order
        from adapters.base import Order
        test_order = Order(
            symbol='0050.TW',
            action='buy',
            quantity=1000,
            price=100.0,
            account_id='paper_001'
        )
        
        preview = await adapter.preview_order(test_order)
        print(f"\n訂單預覽：")
        print(f"  標的：{test_order.symbol}")
        print(f"  動作：{test_order.action}")
        print(f"  數量：{test_order.quantity}")
        print(f"  預估費用：NT$ {preview.fee:,.2f}")
        print(f"  預估稅額：NT$ {preview.tax:,.2f}")
        
        # Submit order
        submitted = await adapter.submit_order(test_order)
        print(f"\n訂單提交：")
        print(f"  狀態：{submitted.status}")
        print(f"  成交價格：{submitted.filled_price}")
        print(f"  成交數量：{submitted.filled_quantity}")
        
        # Get positions
        positions = await adapter.get_positions('paper_001')
        print(f"\n目前持倉：")
        for pos in positions:
            print(f"  - {pos.symbol}: {pos.quantity} 股，均價 {pos.average_price}")
        
    except Exception as e:
        print(f"錯誤：{e}")
        import traceback
        traceback.print_exc()
    print()


async def main():
    """Run all tests."""
    print("\n🚀 Phase 4 - 多券商架構測試\n")
    
    await test_broker_registry()
    await test_account_config()
    await test_adapter_instantiation()
    await test_paper_trading()
    
    print("=" * 72)
    print("✅ Phase 4 測試完成")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
