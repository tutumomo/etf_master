import pytest
from scripts.pre_flight_gate import check_order

def test_ui_flow_state_enforcement():
    context = {'cash': 10000000.0, 'force_trading_hours': False, '_skip_safety_redlines': True}
    
    # 模擬直接 submit (無 preview/confirm flag)
    order_direct_submit = {
        'symbol': '0050', 'side': 'buy', 'quantity': 1000, 
        'price': 150, 'lot_type': 'board',
        'is_submit': True # 標記為實際送單
    }
    res = check_order(order_direct_submit, context)
    assert res['passed'] is False
    assert res['reason'] == 'missing_confirm_flag'

    # 模擬有 confirm flag 的 submit
    order_confirmed_submit = {
        'symbol': '0050', 'side': 'buy', 'quantity': 1000, 
        'price': 150, 'lot_type': 'board',
        'is_submit': True,
        'is_confirmed': True
    }
    res = check_order(order_confirmed_submit, context)
    assert res['passed'] is True

    # 模擬僅 preview，不需 confirm flag
    order_preview = {
        'symbol': '0050', 'side': 'buy', 'quantity': 1000, 
        'price': 150, 'lot_type': 'board',
        'is_submit': False # 僅預覽
    }
    res = check_order(order_preview, context)
    assert res['passed'] is True
