"""
ETF_TW Pro - 模擬盤交易模組
提供虛擬資金進行模擬交易，驗證策略
"""
from db.database import (
    get_portfolio, update_portfolio_cash, 
    get_holdings, add_holding, add_transaction,
    get_transactions, get_portfolio
)
from utils.quote import get_current_price, get_stock_info
from typing import Dict, Optional, Tuple

def get_simulator_status() -> Dict:
    """
    取得模擬盤狀態
    包含：現金、持倉、總資產、損益
    """
    portfolio = get_portfolio()
    holdings = get_holdings()
    
    # 計算持倉總值
    holdings_value = 0
    holding_details = []
    
    for holding in holdings:
        symbol = holding['etf_code']
        quantity = holding['quantity']
        avg_cost = holding['avg_cost']
        
        # 取得目前股價
        current_price = get_current_price(symbol)
        if current_price:
            value = current_price * quantity
            holdings_value += value
            
            # 計算損益
            cost = avg_cost * quantity
            profit_loss = value - cost
            profit_loss_percent = (profit_loss / cost * 100) if cost > 0 else 0
            
            holding_details.append({
                'symbol': symbol,
                'quantity': quantity,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'value': value,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent
            })
    
    # 總資產 = 現金 + 持倉總值
    total_assets = portfolio['cash'] + holdings_value
    initial_cash = portfolio['initial_cash']
    total_profit_loss = total_assets - initial_cash
    total_profit_loss_percent = (total_profit_loss / initial_cash * 100) if initial_cash > 0 else 0
    
    return {
        'cash': portfolio['cash'],
        'initial_cash': initial_cash,
        'holdings_value': holdings_value,
        'total_assets': total_assets,
        'total_profit_loss': total_profit_loss,
        'total_profit_loss_percent': total_profit_loss_percent,
        'holding_details': holding_details
    }

def buy_etf(symbol: str, quantity: int, price: Optional[float] = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    模擬買進 ETF
    回傳：(成功與否, 訊息，交易詳情)
    """
    try:
        # 取得目前股價
        if price is None:
            price = get_current_price(symbol)
            if not price:
                return False, f"❌ 無法取得 {symbol} 目前股價", None
        
        total_cost = price * quantity
        fee = total_cost * 0.001425  # 手續費 0.1425%
        total_amount = total_cost + fee
        
        # 檢查現金是否足夠
        portfolio = get_portfolio()
        if portfolio['cash'] < total_amount:
            return False, f"❌ 現金不足！需要 {total_amount:.2f} 元，目前只有 {portfolio['cash']:.2f} 元", None
        
        # 更新持倉
        add_holding(symbol, quantity, price)
        
        # 更新交易紀錄
        add_transaction(symbol, 'BUY', price, quantity, fee)
        
        # 扣除現金
        new_cash = portfolio['cash'] - total_amount
        update_portfolio_cash(new_cash)
        
        return True, f"✅ 買進成功！{symbol} x {quantity} 股 @ {price:.2f} 元", {
            'symbol': symbol,
            'type': 'BUY',
            'price': price,
            'quantity': quantity,
            'fee': fee,
            'total_amount': total_amount
        }
        
    except Exception as e:
        return False, f"❌ 買進失敗：{str(e)}", None

def sell_etf(symbol: str, quantity: int, price: Optional[float] = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    模擬賣出 ETF
    回傳：(成功與否, 訊息，交易詳情)
    """
    try:
        # 檢查持倉
        holdings = get_holdings()
        holding = next((h for h in holdings if h['etf_code'] == symbol), None)
        
        if not holding or holding['quantity'] < quantity:
            return False, f"❌ 持倉不足！目前持有 {holding['quantity'] if holding else 0} 股", None
        
        # 取得目前股價
        if price is None:
            price = get_current_price(symbol)
            if not price:
                return False, f"❌ 無法取得 {symbol} 目前股價", None
        
        total_value = price * quantity
        fee = total_value * 0.001425  # 手續費 0.1425%
        tax = total_value * 0.003  # 證交稅 0.3%
        total_amount = total_value - fee - tax
        
        # 更新持倉
        add_holding(symbol, -quantity, 0)  # 減少持倉
        
        # 更新交易紀錄
        add_transaction(symbol, 'SELL', price, quantity, fee + tax)
        
        # 增加現金
        portfolio = get_portfolio()
        new_cash = portfolio['cash'] + total_amount
        update_portfolio_cash(new_cash)
        
        return True, f"✅ 賣出成功！{symbol} x {quantity} 股 @ {price:.2f} 元", {
            'symbol': symbol,
            'type': 'SELL',
            'price': price,
            'quantity': quantity,
            'fee': fee + tax,
            'total_amount': total_amount
        }
        
    except Exception as e:
        return False, f"❌ 賣出失敗：{str(e)}", None

def reset_simulator():
    """
    重置模擬盤
    """
    import sqlite3
    conn = sqlite3.connect('db/etf_tw.db')
    cursor = conn.cursor()
    
    # 清空持倉
    cursor.execute('DELETE FROM holdings')
    
    # 清空交易紀錄
    cursor.execute('DELETE FROM transactions')
    
    # 重置現金
    cursor.execute("UPDATE portfolio SET cash = initial_cash WHERE user_id = 'default'")
    
    conn.commit()
    conn.close()
    
    return True, "✅ 模擬盤已重置"

if __name__ == "__main__":
    # 測試模擬盤
    print("🎮 測試模擬盤模組")
    
    # 初始化資料庫
    from db.database import init_db
    init_db()
    
    # 查看模擬盤狀態
    status = get_simulator_status()
    print(f"\n=== 模擬盤狀態 ===")
    print(f"現金：{status['cash']:.2f}")
    print(f"持倉總值：{status['holdings_value']:.2f}")
    print(f"總資產：{status['total_assets']:.2f}")
    print(f"總損益：{status['total_profit_loss']:.2f} ({status['total_profit_loss_percent']:.2f}%)")
    
    # 測試買進
    print(f"\n=== 測試買進 0050.TW ===")
    success, msg, data = buy_etf('0050.TW', 100)
    print(msg)
    
    # 查看最新狀態
    status = get_simulator_status()
    print(f"\n=== 買進後狀態 ===")
    print(f"現金：{status['cash']:.2f}")
    print(f"持倉明細：{status['holding_details']}")
    
    print("\n✅ 模擬盤測試完成")
