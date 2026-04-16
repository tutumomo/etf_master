"""
ETF_TW Pro - 報價模組
串接 Yahoo Finance 取得即時與歷史股價
"""
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

def get_stock_info(symbol: str) -> Optional[Dict]:
    """
    取得股票/ETF 基本資訊
    symbol: 代號 (如：0050.TW, 006208.TW)
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            'symbol': symbol,
            'name': info.get('shortName', ''),
            'price': info.get('regularMarketPrice', 0),
            'previous_close': info.get('previousClose', 0),
            'open': info.get('open', 0),
            'day_high': info.get('dayHigh', 0),
            'day_low': info.get('dayLow', 0),
            'volume': info.get('volume', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', None),
            'dividend_yield': info.get('dividendYield', 0),
            '52_week_high': info.get('fiftyTwoWeekHigh', 0),
            '52_week_low': info.get('fiftyTwoWeekLow', 0),
        }
    except Exception as e:
        print(f"❌ 取得 {symbol} 資訊失敗：{e}")
        return None

def get_current_price(symbol: str) -> Optional[float]:
    """取得目前股價"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return info.get('regularMarketPrice', None)
    except Exception as e:
        print(f"❌ 取得 {symbol} 目前股價失敗：{e}")
        return None

def get_historical_data(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """
    取得歷史股價資料
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        return df
    except Exception as e:
        print(f"❌ 取得 {symbol} 歷史資料失敗：{e}")
        return pd.DataFrame()

def calculate_technical_indicators(symbol: str, period: str = "1mo") -> Dict:
    """
    計算技術指標
    回傳：MA5, MA10, MA20, RSI, MACD 等
    """
    df = get_historical_data(symbol, period)
    
    if df.empty:
        return {}
    
    # 計算移動平均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # 計算 RSI (14 天)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 計算 MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    
    # 取得最後一筆資料
    last = df.iloc[-1]
    
    return {
        'symbol': symbol,
        'timestamp': df.index[-1],
        'close': last['Close'],
        'ma5': last['MA5'],
        'ma10': last['MA10'],
        'ma20': last['MA20'],
        'rsi': last['RSI'],
        'macd': last['MACD'],
        'volume': last['Volume'],
    }

def get_price_change(symbol: str, period: str = "1d") -> Dict:
    """
    取得股價漲跌幅
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, ytd
    """
    df = get_historical_data(symbol, period)
    
    if df.empty:
        return {}
    
    current_price = df['Close'].iloc[-1]
    start_price = df['Close'].iloc[0]
    change = current_price - start_price
    change_percent = (change / start_price) * 100
    
    return {
        'symbol': symbol,
        'current_price': current_price,
        'start_price': start_price,
        'change': change,
        'change_percent': change_percent,
        'period': period,
    }

def scan_etf_list(etf_list: List[str]) -> List[Dict]:
    """
    一次掃描多個 ETF 的即時資訊
    """
    results = []
    for etf in etf_list:
        info = get_stock_info(etf)
        if info:
            results.append(info)
    return results

if __name__ == "__main__":
    # 測試報價模組
    print("📊 測試報價模組")
    
    # 測試 0050.TW
    symbol = "0050.TW"
    print(f"\n=== {symbol} ===")
    
    info = get_stock_info(symbol)
    if info:
        print(f"名稱：{info['name']}")
        print(f"目前價：{info['price']}")
        print(f"漲跌：{info['price'] - info['previous_close']:.2f} ({(info['price'] - info['previous_close'])/info['previous_close']*100:.2f}%)")
    
    # 技術指標
    tech = calculate_technical_indicators(symbol)
    if tech:
        print(f"\n技術指標:")
        print(f"  RSI: {tech.get('rsi', 'N/A'):.2f}" if tech.get('rsi') else "  RSI: N/A")
        print(f"  MA5: {tech.get('ma5', 'N/A'):.2f}" if tech.get('ma5') else "  MA5: N/A")
        print(f"  MA20: {tech.get('ma20', 'N/A'):.2f}" if tech.get('ma20') else "  MA20: N/A")
    
    print("\n✅ 報價模組測試完成")
