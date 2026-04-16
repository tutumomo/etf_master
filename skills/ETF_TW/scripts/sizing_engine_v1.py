import math

def calculate_size(cash, current_holding_value, total_portfolio_value, max_concentration_pct, max_single_limit_twd, risk_temperature, price):
    """
    計算建議下單股數。
    
    Args:
        cash (float): 目前可用現金。
        current_holding_value (float): 目前已持倉該標的的總價值。
        total_portfolio_value (float): 帳戶總資產價值 (現金 + 持倉市值)。
        max_concentration_pct (float): 個股集中度上限 (0.0~1.0)。
        max_single_limit_twd (float): 單筆交易 TWD 上限。
        risk_temperature (float): 風險溫度 (0.0~1.0)。
        price (float): 當前每股價格。
        
    Returns:
        dict: 包含建議股數 (quantity), 是否可下單 (can_order), 限制原因 (reason) 等。
    """
    if price <= 0:
        return {
            'quantity': 0,
            'can_order': False,
            'reason': 'invalid_price',
            'base_amount': 0,
            'limit_amount': 0
        }
        
    # 修正 WR-01: 考慮現有持倉與總資產
    # 1. 該標的允許持有的最大價值 = 總資產 * 集中度上限
    max_allowed_value = total_portfolio_value * max_concentration_pct
    
    # 2. 目前剩餘可買入額度 = max(0, 允許最大價值 - 現有持倉價值)
    available_quota = max(0, max_allowed_value - current_holding_value)
    
    # 3. 基本購買量 = min(剩餘可用現金, 剩餘可買額度) * 風險溫度
    # 注意：不能超過手上有的現金
    base_amount = min(cash, available_quota) * risk_temperature
    
    # 4. 限制量 = min(基本購買量, 單筆交易上限)
    limit_amount = min(base_amount, max_single_limit_twd)
    
    # 5. 建議股數 = 限制量 // 當前價格
    quantity = int(limit_amount // price)
    
    reason = 'within_limits'
    if base_amount > max_single_limit_twd:
        reason = 'single_limit_hit'
    elif quantity == 0:
        if available_quota <= 0:
            reason = 'concentration_limit_hit'
        else:
            reason = 'insufficient_funds'
        
    return {
        'quantity': quantity,
        'can_order': quantity > 0,
        'reason': reason,
        'base_amount': base_amount,
        'limit_amount': limit_amount,
        'available_quota': available_quota
    }
