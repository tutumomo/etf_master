import unittest
from unittest.mock import patch, MagicMock
from scripts.pre_flight_gate import check_order

class TestSafetyRedlines(unittest.TestCase):
    def setUp(self):
        self.context = {
            'cash': 1000000.0,
            'max_concentration_pct': 0.3,
            'max_single_limit_twd': 500000.0,
            'risk_temperature': 1.0,
            'inventory': {},
            'force_trading_hours': False
        }
        self.default_redlines = {
            "max_buy_amount_twd": 500000.0,
            "max_buy_amount_pct": 50.0,
            "max_buy_shares": 1000,
            "max_concentration_pct": 30.0,
            "daily_loss_limit_pct": 5.0,
            "ai_confidence_threshold": 0.7,
            "enabled": True
        }
        self.default_pnl = {
            "circuit_breaker_triggered": False
        }

    @patch('scripts.pre_flight_gate.load_safety_data')
    def test_max_shares_blocking(self, mock_load):
        # 測試買入 2000 股 (當上限為 1000 股時) 被阻斷
        mock_load.return_value = {
            "redlines": {**self.default_redlines, "max_buy_shares": 1000},
            "pnl": self.default_pnl
        }
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 2000, 'price': 100}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'redline_shares_exceeded')

    @patch('scripts.pre_flight_gate.load_safety_data')
    def test_max_amount_twd_blocking(self, mock_load):
        # 測試買入 100 萬 TWD (當上限為 50 萬時) 被紅線阻斷
        # 移除 max_single_limit_twd 避免在 sizing step 就被攔截
        mock_load.return_value = {
            "redlines": {**self.default_redlines, "max_buy_amount_twd": 500000.0},
            "pnl": self.default_pnl
        }
        ctx = {**self.context, 'max_single_limit_twd': None, 'max_concentration_pct': None}
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 10000, 'price': 100}
        result = check_order(order, ctx)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'redline_amount_exceeded')

    def test_max_amount_pct_blocking(self):
        # max_buy_amount_pct 已整合進 sizing limit (step 5)
        # max_single_limit_twd=500,000; 6000×100=600,000 超過 → exceeds_sizing_limit
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 6000, 'price': 100}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'exceeds_sizing_limit')

    @patch('scripts.pre_flight_gate.load_safety_data')
    def test_daily_loss_circuit_breaker(self, mock_load):
        # 模擬 circuit_breaker_triggered: true 並驗證所有買入被阻斷
        mock_load.return_value = {
            "redlines": self.default_redlines,
            "pnl": {"circuit_breaker_triggered": True}
        }
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 100, 'price': 100}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'circuit_breaker_triggered')
        
        # 賣出不應受影響
        order_sell = {'symbol': '0050', 'side': 'sell', 'quantity': 100, 'price': 100}
        # Mock inventory to allow sell
        self.context['inventory'] = {'0050': 200}
        result_sell = check_order(order_sell, self.context)
        self.assertTrue(result_sell['passed'])

    @patch('scripts.pre_flight_gate.load_safety_data')
    def test_ai_confidence_blocking(self, mock_load):
        # 模擬 AI 信心 0.5 (當門檻 0.7 時) 並驗證被阻斷
        mock_load.return_value = {
            "redlines": {**self.default_redlines, "ai_confidence_threshold": 0.7},
            "pnl": self.default_pnl
        }
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 100, 'price': 100, 'ai_confidence': 0.5}
        result = check_order(order, self.context)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'low_ai_confidence')

    @patch('scripts.pre_flight_gate.load_safety_data')
    def test_safety_redlines_disabled(self, mock_load):
        # 驗證紅線系統 enabled: false 時不影響正常交易
        mock_load.return_value = {
            "redlines": {**self.default_redlines, "enabled": False, "max_buy_shares": 10},
            "pnl": self.default_pnl
        }
        order = {'symbol': '0050', 'side': 'buy', 'quantity': 100, 'price': 100}
        result = check_order(order, self.context)
        self.assertTrue(result['passed'])

if __name__ == '__main__':
    unittest.main()
