import unittest
from unittest.mock import patch
from scripts.pre_flight_gate import check_order

class TestFuseV1(unittest.TestCase):
    def setUp(self):
        self.context = {
            'cash': 1000000.0,
            'max_concentration_pct': 0.3,
            'max_single_limit_twd': 200000.0,
            'risk_temperature': 1.0,
            'inventory': {'0050': 0, '006208': 0}, # 預設空倉，避免干擾買入測試
            'force_trading_hours': False,
            '_skip_safety_redlines': True,  # 測試不依賴 instance state 的 safety_redlines.json
        }

    def test_invalid_quantity(self):
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 0, 'price': 150}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'invalid_quantity')

    def test_invalid_price(self):
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 1000, 'price': 0}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'invalid_price')

    def test_buy_over_limit(self):
        # max_single_limit_twd = 200,000, price=150
        # 200,000 // 150 = 1,333
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 2000, 'price': 150, 'lot_type': 'board'}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'exceeds_sizing_limit')

    def test_sell_insufficient_inventory(self):
        order = {'symbol': '0050', 'side': 'sell', 'quantity': 3000, 'price': 150}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'insufficient_inventory')

    def test_board_lot_unit_check(self):
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 500, 'price': 150, 'lot_type': 'board'}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'invalid_unit_for_board_lot')

    def test_odd_lot_unit_check(self):
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 1000, 'price': 150, 'lot_type': 'odd'}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'invalid_unit_for_odd_lot')

    @patch('scripts.pre_flight_gate.get_trading_hours_info')
    def test_trading_hours_blocking(self, mock_hours):
        mock_hours.return_value = {'is_trading_hours': False, 'current_time': '15:00'}
        self.context['force_trading_hours'] = True
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 1000, 'price': 150, 'lot_type': 'board'}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'outside_trading_hours')

    def test_successful_buy(self):
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 1000, 'price': 150, 'lot_type': 'board'}
        result = check_order(order, self.context)
        self.assertTrue(result['passed'])

    def test_successful_sell(self):
        self.context['inventory']['0050'] = 2000
        order = {'symbol': '0050', 'side': 'sell', 'quantity': 1000, 'price': 150, 'lot_type': 'board'}
        result = check_order(order, self.context)
        self.assertTrue(result['passed'])

if __name__ == '__main__':
    unittest.main()
