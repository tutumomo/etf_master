import pytest
import pandas as pd
import numpy as np
from scripts.etf_core.data_engine import get_history, get_ma

def test_get_history_period():
    # 測試是否支援週期參數
    data = get_history('0050.TW', period='w')
    assert isinstance(data, pd.DataFrame)
    assert not data.empty

def test_get_ma():
    # 測試 MA 計算
    data = pd.DataFrame({'Close': [100, 102, 104, 106, 108, 110]})
    ma = get_ma(data, [5])
    assert 'MA5' in ma.columns
    assert not np.isnan(ma['MA5'].iloc[-1])
