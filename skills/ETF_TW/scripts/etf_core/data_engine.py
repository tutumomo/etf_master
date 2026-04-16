import yfinance as yf
import pandas as pd

PERIOD_MAP = {
    'd': '1mo',
    'w': '3mo',
    'm': '1y',
    'q': '2y',
    'y': '5y'
}

def get_history(symbol: str, period: str = 'd') -> pd.DataFrame:
    yf_period = PERIOD_MAP.get(period, '1mo')
    ticker = yf.Ticker(symbol)
    # yfinance 對週資料、月資料處理方式不同，這裡簡單用 interval 處理
    interval = '1d'
    if period == 'w':
        interval = '1wk'
    elif period in ['m', 'q', 'y']:
        interval = '1mo'
        
    return ticker.history(period=yf_period, interval=interval)

def get_ma(data: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    df = data.copy()
    for window in windows:
        df[f'MA{window}'] = df['Close'].rolling(window=window).mean()
    return df
