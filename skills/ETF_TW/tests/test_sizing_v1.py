import unittest
from scripts.sizing_engine_v1 import calculate_size

class TestSizingEngineV1(unittest.TestCase):
    def test_basic_calculation(self):
        # cash=1,000,000, current_holding=0, total=1,000,000, max_concentration=0.3, max_single=200,000, risk=1.0, price=100
        # max_allowed = 1,000,000 * 0.3 = 300,000
        # quota = 300,000 - 0 = 300,000
        # base = min(1,000,000, 300,000) * 1.0 = 300,000
        # limit = min(300,000, 200,000) = 200,000
        # quantity = 200,000 // 100 = 2,000
        result = calculate_size(1000000, 0, 1000000, 0.3, 200000, 1.0, 100)
        self.assertEqual(result['quantity'], 2000)
        self.assertTrue(result['can_order'])

    def test_risk_temperature(self):
        # cash=1,000,000, current_holding=0, total=1,000,000, max_concentration=0.3, max_single=500,000, risk=0.5, price=100
        # max_allowed = 1,000,000 * 0.3 = 300,000
        # quota = 300,000
        # base = min(1,000,000, 300,000) * 0.5 = 150,000
        # limit = min(150,000, 500,000) = 150,000
        # quantity = 150,000 // 100 = 1,500
        result = calculate_size(1000000, 0, 1000000, 0.3, 500000, 0.5, 100)
        self.assertEqual(result['quantity'], 1500)

    def test_single_limit_bottleneck(self):
        # cash=10,000,000, current_holding=0, total=10,000,000, max_concentration=0.3, max_single=200,000, risk=1.0, price=100
        # max_allowed = 3,000,000
        # base = 3,000,000
        # limit = min(3,000,000, 200,000) = 200,000
        result = calculate_size(10000000, 0, 10000000, 0.3, 200000, 1.0, 100)
        self.assertEqual(result['quantity'], 2000)
        self.assertEqual(result['reason'], 'single_limit_hit')

    def test_zero_price(self):
        result = calculate_size(1000000, 0, 1000000, 0.3, 200000, 1.0, 0)
        self.assertEqual(result['quantity'], 0)
        self.assertFalse(result['can_order'])

    def test_insufficient_cash(self):
        result = calculate_size(100, 0, 1000, 0.3, 200000, 1.0, 1000)
        self.assertEqual(result['quantity'], 0)
        self.assertFalse(result['can_order'])
        self.assertEqual(result['reason'], 'insufficient_funds')

    def test_concentration_limit(self):
        # 修正 WR-01 測試
        # 總資產 100 萬，限制 30% (30 萬)，已持有 25 萬
        # 剩餘額度 = 5 萬
        # 現金雖然有 100 萬，但受限於集中度只能再買 5 萬
        result = calculate_size(1000000, 250000, 1000000, 0.3, 200000, 1.0, 100)
        self.assertEqual(result['quantity'], 500)
        self.assertEqual(result['available_quota'], 50000)
        
        # 已達上限測試
        result = calculate_size(1000000, 300000, 1000000, 0.3, 200000, 1.0, 100)
        self.assertEqual(result['quantity'], 0)
        self.assertEqual(result['reason'], 'concentration_limit_hit')

if __name__ == '__main__':
    unittest.main()
