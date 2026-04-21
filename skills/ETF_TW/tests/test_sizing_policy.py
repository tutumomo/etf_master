import pytest
from scripts.pre_flight_gate import check_order

def test_dynamic_sizing_policy():
    # 變更前：政策上限 30% 現金，單筆上限 50萬
    context_v1 = {
        'cash': 1000000.0,
        'max_concentration_pct': 0.3, # 最多 30萬
        'max_single_limit_twd': 500000.0,
        'risk_temperature': 1.0,
        'force_trading_hours': False,
        '_skip_safety_redlines': True,
    }

    # 要買 150元 的股票，1張 (1000股) 要 15萬
    # 如果買 3張 = 45萬，會超過 30萬的濃度限制 (0.3)
    order_3_lots = {
        'symbol': '0050', 'side': 'buy', 'quantity': 3000, 
        'price': 150, 'lot_type': 'board',
        'is_submit': False # 僅預覽
    }
    res_v1 = check_order(order_3_lots, context_v1)
    assert res_v1['passed'] is False
    assert res_v1['reason'] == 'exceeds_sizing_limit'
    assert res_v1['details']['allowed'] == 2000 # (100萬 * 0.3) / 150 = 300000 / 150 = 2000 股 = 2張

    # 變更後：放寬政策，現金比例上限至 50%
    context_v2 = {
        'cash': 1000000.0,
        'max_concentration_pct': 0.5, # 最多 50萬
        'max_single_limit_twd': 500000.0,
        'risk_temperature': 1.0,
        'force_trading_hours': False,
        '_skip_safety_redlines': True,
    }
    
    # 這次買 3張 = 45萬，不超過 50萬 (50%)
    res_v2 = check_order(order_3_lots, context_v2)
    assert res_v2['passed'] is True
