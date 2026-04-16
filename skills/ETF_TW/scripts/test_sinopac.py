#!/usr/bin/env python3
"""
Test script for Sinopac Adapter (Phase 5).

Tests the scaffold implementation of SinoPac Securities adapter.
"""

import asyncio
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from adapters.sinopac_adapter import SinopacAdapter, create_sinopac_adapter


async def test_sinopac_adapter():
    """Test Sinopac adapter scaffold."""
    print("=" * 72)
    print("測試：永豐金證券適配器（Scaffold）")
    print("=" * 72)
    
    # Create adapter
    config = {
        'api_key': 'YOUR_API_KEY',
        'secret_key': 'YOUR_SECRET_KEY',
        'password': 'YOUR_PASSWORD',
        'mode': 'paper'  # Simulation mode
    }
    
    adapter = create_sinopac_adapter(config)
    
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
            print(f"   - {pos.symbol}: {pos.quantity} 股")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    # Test 5: Order preview
    print("\n5. 測試訂單預覽")
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
    except Exception as e:
        print(f"   錯誤：{e}")
    
    # Test 6: Order validation
    print("\n6. 測試訂單驗證")
    try:
        is_valid, warnings = await adapter.validate_order(test_order)
        print(f"   驗證結果：{'有效' if is_valid else '無效'}")
        if warnings:
            print(f"   警告：{', '.join(warnings)}")
    except Exception as e:
        print(f"   錯誤：{e}")
    
    print("\n" + "=" * 72)
    print("✅ 永豐金證券適配器測試完成")
    print("=" * 72)
    print("\n注意：此為 Scaffold 實作，尚未連接真實 API")
    print("實際交易需要：")
    print("  1. 永豐金證券 API 憑證")
    print("  2. 真實的證券帳戶")
    print("  3. 完整的 API 對接實作")


if __name__ == "__main__":
    asyncio.run(test_sinopac_adapter())
