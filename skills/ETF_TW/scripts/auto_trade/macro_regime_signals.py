"""
Macro regime signals (top-down 大盤訊號)
========================================

提供三個獨立宏觀訊號，融入 generate_taiwan_market_context 的投票機制：

  1. twii_vs_200ma_pct  — ^TWII 收盤對 200MA 的偏離百分比
  2. vix                — ^VIX 當前值（用美股 VIX 代理台股 VIX 流動性問題）
  3. twii_60d_percentile — ^TWII 在過去 60 個交易日的價格百分位

每個訊號獨立貢獻 -1 / 0 / +1 票，加總得 macro_score (-3 ~ +3)。

設計原則：
  - 純函式，沒有副作用
  - yfinance 抓取失敗 → 訊號回 None，不 crash
  - 缺值的訊號 → 該票記為 0（中性），不影響其他訊號
  - 門檻是經驗值，可調整但需有單元測試保護

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 A，修訂版 v2)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class MacroSignals:
    """三個 macro 訊號的容器；任一為 None 表示無資料。"""
    twii_vs_200ma_pct: Optional[float]
    vix: Optional[float]
    twii_60d_percentile: Optional[float]

    def to_dict(self) -> dict:
        return {
            "twii_vs_200ma_pct": self.twii_vs_200ma_pct,
            "vix": self.vix,
            "twii_60d_percentile": self.twii_60d_percentile,
        }


# ---------------------------------------------------------------------------
# Threshold constants — 經驗值，由單元測試鎖定
# ---------------------------------------------------------------------------

TWII_VS_200MA_BULL_THRESHOLD = 5.0    # 偏離 +5% 以上 → +1 票
TWII_VS_200MA_BEAR_THRESHOLD = -5.0   # 偏離 -5% 以下 → -1 票
TWII_VS_200MA_OVERHEAT_THRESHOLD = 25.0  # 偏離 +25% 以上 → 過熱反轉風險，-1 票（mean reversion）

VIX_LOW_THRESHOLD = 20.0              # < 20 → +1 票
VIX_HIGH_THRESHOLD = 30.0             # > 30 → -1 票

PERCENTILE_HIGH_THRESHOLD = 70.0      # > 70% → +1 票（高檔但仍偏多訊號）
PERCENTILE_LOW_THRESHOLD = 30.0       # < 30% → -1 票

WINDOW_200MA = 200
WINDOW_PERCENTILE = 60


# ---------------------------------------------------------------------------
# Signal computations
# ---------------------------------------------------------------------------

def compute_twii_vs_200ma(history) -> Optional[float]:
    """
    計算 ^TWII 收盤對 200MA 的偏離百分比。

    Args:
        history: yfinance Ticker.history(period='1y') 回傳的 DataFrame
                 必須含 'Close' 欄與至少 200 筆資料

    Returns:
        偏離百分比（正值=高於 200MA）；資料不足或空回傳 None
    """
    if history is None:
        return None
    try:
        if len(history) < WINDOW_200MA:
            return None
        close = history["Close"]
        ma200 = close.tail(WINDOW_200MA).mean()
        if ma200 <= 0:
            return None
        current = float(close.iloc[-1])
        return (current - float(ma200)) / float(ma200) * 100.0
    except Exception:
        return None


def compute_60d_percentile(history) -> Optional[float]:
    """
    計算 current price 在過去 60 個交易日內的百分位 (0~100)。

    100 = 60 日新高
    0   = 60 日新低
    50  = 處於中位

    Args:
        history: yfinance Ticker.history(period='3mo') 即可
                 必須含 'Close' 欄與至少 60 筆資料

    Returns:
        百分位 0~100；資料不足回 None
    """
    if history is None:
        return None
    try:
        if len(history) < WINDOW_PERCENTILE:
            return None
        close = history["Close"]
        window = close.tail(WINDOW_PERCENTILE)
        current = float(close.iloc[-1])
        rank = (window < current).sum()  # 嚴格小於 current 的筆數
        return float(rank) / float(WINDOW_PERCENTILE) * 100.0
    except Exception:
        return None


def compute_vix(vix_history) -> Optional[float]:
    """從 ^VIX history 取最新值；空回傳 None。"""
    if vix_history is None:
        return None
    try:
        if len(vix_history) == 0:
            return None
        return float(vix_history["Close"].iloc[-1])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Score & classification
# ---------------------------------------------------------------------------

def _vote_twii_ma(pct: Optional[float]) -> int:
    """
    投票規則（含 mean reversion 警示）：
      pct > +25%  → -1（過熱，反轉風險高於趨勢延續）
      +5% < pct <= +25% → +1（健康偏多）
      -5% <= pct <= +5% → 0（中性）
      pct < -5% → -1（偏弱）
    """
    if pct is None:
        return 0
    if pct > TWII_VS_200MA_OVERHEAT_THRESHOLD:
        return -1  # 過熱倒扣 — 24,000 點還在追的對策
    if pct > TWII_VS_200MA_BULL_THRESHOLD:
        return 1
    if pct < TWII_VS_200MA_BEAR_THRESHOLD:
        return -1
    return 0


def _vote_vix(vix: Optional[float]) -> int:
    if vix is None:
        return 0
    if vix < VIX_LOW_THRESHOLD:
        return 1
    if vix > VIX_HIGH_THRESHOLD:
        return -1
    return 0


def _vote_percentile(pct: Optional[float]) -> int:
    if pct is None:
        return 0
    if pct > PERCENTILE_HIGH_THRESHOLD:
        return 1
    if pct < PERCENTILE_LOW_THRESHOLD:
        return -1
    return 0


def compute_macro_score(signals: MacroSignals) -> int:
    """
    三訊號各投 -1/0/+1，加總範圍 -3 ~ +3。
    缺值訊號記 0（中性）。
    """
    return (
        _vote_twii_ma(signals.twii_vs_200ma_pct)
        + _vote_vix(signals.vix)
        + _vote_percentile(signals.twii_60d_percentile)
    )


def classify_macro_regime(signals: MacroSignals) -> str:
    """
    高階分類，僅用於 dashboard 顯示與 audit log，
    真正的決策仍由 macro_score 加入主投票表。

    score >= 2 → macro_bullish
    score <= -2 → macro_cautious
    其他 → macro_neutral
    """
    score = compute_macro_score(signals)
    if score >= 2:
        return "macro_bullish"
    if score <= -2:
        return "macro_cautious"
    return "macro_neutral"


# ---------------------------------------------------------------------------
# yfinance fetch wrappers (薄層；測試時 mock 不到這層)
# ---------------------------------------------------------------------------

def fetch_macro_signals(
    twii_ticker: str = "^TWII",
    vix_ticker: str = "^VIX",
) -> MacroSignals:
    """
    從 yfinance 抓 ^TWII 與 ^VIX，計算三個訊號。
    任一抓取失敗的訊號回 None，不影響其他。

    Note:
      - period='1y' 給 200MA 計算（約 250 個交易日）
      - period='3mo' 給 60D percentile 計算
      - VIX 只需 period='5d' 取最新即可
    """
    twii_pct = None
    percentile = None
    vix_value = None

    try:
        import yfinance as yf
    except Exception:
        return MacroSignals(None, None, None)

    # ^TWII for 200MA + 60D percentile
    try:
        twii = yf.Ticker(twii_ticker)
        hist = twii.history(period="1y", auto_adjust=False)
        twii_pct = compute_twii_vs_200ma(hist)
        percentile = compute_60d_percentile(hist)
    except Exception:
        pass

    # ^VIX
    try:
        vix = yf.Ticker(vix_ticker)
        vix_hist = vix.history(period="5d", auto_adjust=False)
        vix_value = compute_vix(vix_hist)
    except Exception:
        pass

    return MacroSignals(
        twii_vs_200ma_pct=twii_pct,
        vix=vix_value,
        twii_60d_percentile=percentile,
    )
