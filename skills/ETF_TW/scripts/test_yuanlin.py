#!/usr/bin/env python3
"""
Test script for Yuanlin (Yuanta) Adapter.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adapters.yuanlin_adapter import YuanlinAdapter, create_yuanlin_adapter


async def test_yuanlin_adapter():
    """Test Yuanlin adapter scaffold."""
    print("=" * 72)
    print("測試：元大證券適配器（Scaffold）")
    print("=" * 72)
    
    config = {
        'account_id': 'test_account',
        'password': 'test_password',
        'trade_password': 'test_trade_password',
        'api_url': 'https://api.yuanta.com.tw'
    }
    
    adapter = create_yuanlin_adapter(config)
    
    # Test 1: Authentication
    print("\n1. 測試認證")
    auth_result = await adapter.authenticate()
    print(f"   認證結果：{'成功' if auth_result else '失敗'}")
    
    if not auth_result:
        print("   認證失敗，終止測試")
        return
    
    # Test 2: Market data
    print("\n2. 測試市場資料查詢")
    try:
        market_data = await adapter.get_market_data('0050.TW')
        print(f"   標的：{market_data['symbol']}")
        print(f"   價格：{market_data['price']}")
        print(f"   漲跌：{market_data['change']}")
        print(f"   本益比：{market_data.get('pe_ratio', 'N/A')}")
        print(f"   殖利率：{market_data.get('dividend_yield', 'N/A')}")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    # Test 3: Account balance
    print("\n3. 測試帳戶餘額查詢")
    try:
        balance = await adapter.get_account_balance('test_account')
        print(f"   可用餘額：NT$ {balance.cash_available:,.0f}")
        print(f"   可買權限：NT$ {balance.buying_power:,.0f}")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    # Test 4: Positions
    print("\n4. 測試持倉查詢")
    try:
        positions = await adapter.get_positions('test_account')
        print(f"   持倉筆數：{len(positions)}")
        for pos in positions:
            print(f"   - {pos.symbol}: {pos.quantity} 股，未實現損益 {pos.unrealized_pnl}")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    # Test 5: Order preview with ETF discount
    print("\n5. 測試訂單預覽（含 ETF 優惠）")
    try:
        from adapters.base import Order
        test_order = Order(
            symbol='0050.TW',
            action='buy',
            quantity=1000,
            price=100.0,
            account_id='test_account'
        )
        
        preview = await adapter.preview_order(test_order)
        print(f"   預估費用：NT$ {preview.fee:,.2f}")
        print(f"   預估稅額：NT$ {preview.tax:,.2f}")
        print(f"   （已套用 ETF 手續費折扣）")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    print("\n" + "=" * 72)
    print("✅ 元大證券適配器測試完成")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(test_yuanlin_adapter())
