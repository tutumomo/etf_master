#!/usr/bin/env python3
"""
vwap_calculator.py — 30 分鐘 VWAP 計算器

買入掃描在 09:30 / 11:00 / 13:00 三個時點觸發，每次計算
「該時點前 30 分鐘的 VWAP（成交量加權均價）」與昨收比較。

VWAP 公式：Σ(price × volume) / Σ(volume)
  - price 用該分鐘的 typical price = (high + low + close) / 3
  - volume 用該分鐘的成交量

資料來源：yfinance Ticker.history(period='1d', interval='1m')
  - 注意：yfinance 對台灣股市約 15 分鐘延遲，這是已知限制

時區處理：所有時間都用 Asia/Taipei (TW_TZ)。
yfinance 回傳的 DatetimeIndex 帶時區，會轉成 TW_TZ 再計算。

邊界處理：
  - 若指定區間內資料不足 5 分鐘 → 回傳 None + warning='insufficient_data'
  - 若 yfinance 回傳空 DataFrame → 回傳 None + warning='no_data'
  - 若所有 volume 都是 0（停牌？）→ 回傳 None + warning='zero_volume'
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None

TW_TZ = ZoneInfo("Asia/Taipei")

# 三個觸發時點（買入）
BUY_TRIGGER_TIMES: tuple[time, ...] = (
    time(9, 30),
    time(11, 0),
    time(13, 0),
)

# 賣出觸發時點
SELL_TRIGGER_TIME = time(13, 15)

# VWAP 回看視窗（分鐘）
VWAP_WINDOW_MINUTES = 30

# 最少有效分鐘數（少於此值視為資料不足）
MIN_VALID_MINUTES = 5


@dataclass
class VWAPResult:
    """VWAP 計算結果"""
    symbol: str
    vwap: float | None              # None 表示資料不足
    typical_window_minutes: int     # 實際使用的分鐘數
    start_time: str                 # ISO8601 with TW_TZ
    end_time: str
    sample_count: int               # 該區間實際取得的 bar 數
    warning: str | None = None      # 'insufficient_data' / 'no_data' / 'zero_volume' / None


def _to_tw_tz(dt: datetime) -> datetime:
    """確保 datetime 為 Asia/Taipei tzaware"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TW_TZ)
    return dt.astimezone(TW_TZ)


def fetch_1m_quotes(symbol: str, ticker_suffix: str = ".TW") -> Any:
    """
    從 yfinance 抓當日 1 分鐘 K 線。

    Args:
        symbol: '00923' / '0050'
        ticker_suffix: '.TW' 或 '.TWO'

    Returns:
        pandas.DataFrame（columns: Open/High/Low/Close/Volume，index 為 tz-aware DatetimeIndex）
        若失敗回傳 None。
    """
    if yf is None:
        return None
    full_ticker = f"{symbol}{ticker_suffix}" if "." not in symbol else symbol
    try:
        ticker = yf.Ticker(full_ticker)
        hist = ticker.history(period="1d", interval="1m")
        if hist is None or hist.empty:
            return None
        # 確保 index 是 tz-aware 且為 TW_TZ
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC").tz_convert(TW_TZ)
        else:
            hist.index = hist.index.tz_convert(TW_TZ)
        return hist
    except Exception:
        return None


def compute_vwap(
    quotes,  # pandas.DataFrame
    start_time: datetime,
    end_time: datetime,
) -> tuple[float | None, int, str | None]:
    """
    計算指定時間區間的 VWAP。

    Args:
        quotes: 1m K 線 DataFrame（index 為 TW_TZ datetime）
        start_time: 區間開始（含）
        end_time: 區間結束（不含）

    Returns:
        (vwap, sample_count, warning)
        vwap 為 None 表示無法計算
    """
    if quotes is None or len(quotes) == 0:
        return None, 0, "no_data"

    start_tw = _to_tw_tz(start_time)
    end_tw = _to_tw_tz(end_time)

    # 篩選區間
    mask = (quotes.index >= start_tw) & (quotes.index < end_tw)
    window = quotes.loc[mask]
    sample_count = len(window)

    if sample_count == 0:
        return None, 0, "no_data"
    if sample_count < MIN_VALID_MINUTES:
        return None, sample_count, "insufficient_data"

    # typical price = (high + low + close) / 3
    typical = (window["High"] + window["Low"] + window["Close"]) / 3.0
    volume = window["Volume"]

    total_volume = float(volume.sum())
    if total_volume <= 0:
        return None, sample_count, "zero_volume"

    weighted_sum = float((typical * volume).sum())
    vwap = weighted_sum / total_volume
    return round(vwap, 4), sample_count, None


def compute_vwap_for_trigger(
    symbol: str,
    trigger_time: time,
    *,
    on_date: datetime | None = None,
    ticker_suffix: str = ".TW",
    quotes_override=None,  # for testing
) -> VWAPResult:
    """
    計算「指定觸發時點之前 30 分鐘」的 VWAP。

    例：trigger_time=09:30 → 計算 09:00–09:30 的 VWAP
        trigger_time=11:00 → 計算 10:30–11:00 的 VWAP

    Args:
        symbol: 股票代號（不含 .TW）
        trigger_time: 觸發時點（time 物件）
        on_date: 指定日期，預設為今天
        ticker_suffix: yfinance ticker 後綴
        quotes_override: 測試用，直接傳入 DataFrame 跳過 yfinance

    Returns:
        VWAPResult
    """
    base_date = (on_date or datetime.now(tz=TW_TZ)).date()
    end_dt = datetime.combine(base_date, trigger_time, tzinfo=TW_TZ)
    start_dt = end_dt - timedelta(minutes=VWAP_WINDOW_MINUTES)

    quotes = quotes_override if quotes_override is not None else fetch_1m_quotes(symbol, ticker_suffix)
    vwap, sample_count, warning = compute_vwap(quotes, start_dt, end_dt)

    return VWAPResult(
        symbol=symbol,
        vwap=vwap,
        typical_window_minutes=VWAP_WINDOW_MINUTES,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        sample_count=sample_count,
        warning=warning,
    )


def is_within_trigger_window(now: datetime, trigger: time, *, tolerance_min: int = 5) -> bool:
    """
    判斷當前時間是否在觸發時點 ± tolerance 範圍內。

    用於 cron 每分鐘檢查時的觸發判定。
    """
    now_tw = _to_tw_tz(now)
    trigger_dt = datetime.combine(now_tw.date(), trigger, tzinfo=TW_TZ)
    delta = abs((now_tw - trigger_dt).total_seconds()) / 60
    return delta <= tolerance_min


def find_active_trigger(now: datetime, *, tolerance_min: int = 5) -> time | None:
    """
    回傳當下處於哪個觸發時點（買入或賣出）。
    若不在任何觸發窗，回傳 None。
    """
    for t in (*BUY_TRIGGER_TIMES, SELL_TRIGGER_TIME):
        if is_within_trigger_window(now, t, tolerance_min=tolerance_min):
            return t
    return None
