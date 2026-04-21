import pytest
from scripts.pre_flight_gate import check_order

def test_unit_and_odd_lot_validation():
    context = {'cash': 10000000.0, 'force_trading_hours': False, '_skip_safety_redlines': True}

    # TEST-01: 驗證 Common 張數與 IntradayOdd 股數
    # 預期：board (Common) 需要是 1000 的倍數
    order_board_valid = {'symbol': '0050', 'side': 'buy', 'quantity': 2000, 'price': 150, 'lot_type': 'board'}
    res = check_order(order_board_valid, context)
    assert res['passed'] is True

    order_board_invalid = {'symbol': '0050', 'side': 'buy', 'quantity': 1500, 'price': 150, 'lot_type': 'board'}
    res = check_order(order_board_invalid, context)
    assert res['passed'] is False
    assert res['reason'] == 'invalid_unit_for_board_lot'

    # 預期：odd (IntradayOdd) 需要是 1-999 股
    order_odd_valid = {'symbol': '0050', 'side': 'buy', 'quantity': 500, 'price': 150, 'lot_type': 'odd'}
    res = check_order(order_odd_valid, context)
    assert res['passed'] is True

    order_odd_invalid = {'symbol': '0050', 'side': 'buy', 'quantity': 1500, 'price': 150, 'lot_type': 'odd'}
    res = check_order(order_odd_invalid, context)
    assert res['passed'] is False
    assert res['reason'] == 'invalid_unit_for_odd_lot'

def test_zero_or_negative_quantity():
    context = {'cash': 10000000.0, 'force_trading_hours': False}
    order_zero = {'symbol': '0050', 'side': 'buy', 'quantity': 0, 'price': 150}
    res = check_order(order_zero, context)
    assert res['passed'] is False
    assert res['reason'] == 'invalid_quantity'

    order_negative = {'symbol': '0050', 'side': 'buy', 'quantity': -100, 'price': 150}
    res = check_order(order_negative, context)
    assert res['passed'] is False
    assert res['reason'] == 'invalid_quantity'
