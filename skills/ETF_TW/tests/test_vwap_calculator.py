"""
Tests for auto_trade.vwap_calculator:
  - compute_vwap basic correctness
  - boundary conditions (no_data / insufficient_data / zero_volume)
  - timezone handling
  - is_within_trigger_window / find_active_trigger
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

pd = pytest.importorskip("pandas")

from scripts.auto_trade.vwap_calculator import (
    BUY_TRIGGER_TIMES,
    SELL_TRIGGER_TIME,
    TW_TZ,
    VWAPResult,
    compute_vwap,
    compute_vwap_for_trigger,
    find_active_trigger,
    is_within_trigger_window,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_quotes(start: datetime, n: int, *, prices=None, volumes=None):
    """產生 n 分鐘的 1m K 線測試資料。"""
    if prices is None:
        prices = [100.0] * n
    if volumes is None:
        volumes = [1000] * n
    idx = pd.DatetimeIndex(
        [start + timedelta(minutes=i) for i in range(n)],
        tz=TW_TZ,
    )
    df = pd.DataFrame(
        {
            "Open": prices,
            "High": [p + 0.5 for p in prices],
            "Low": [p - 0.5 for p in prices],
            "Close": prices,
            "Volume": volumes,
        },
        index=idx,
    )
    return df


# ---------------------------------------------------------------------------
# compute_vwap basic correctness
# ---------------------------------------------------------------------------

def test_compute_vwap_uniform_prices():
    """所有分鐘價格相同 → VWAP 應等於該價格"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start, 30, prices=[100.0] * 30)
    end = start + timedelta(minutes=30)
    vwap, n, warn = compute_vwap(quotes, start, end)
    assert warn is None
    assert n == 30
    # typical = (100.5 + 99.5 + 100) / 3 = 100.0
    assert vwap == pytest.approx(100.0, abs=0.01)


def test_compute_vwap_volume_weighted():
    """高成交量分鐘的價格應主導 VWAP"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    # 前 5 分鐘 100 元 大量；後 5 分鐘 110 元 小量
    prices = [100.0] * 5 + [110.0] * 5
    volumes = [10000] * 5 + [100] * 5
    quotes = _make_quotes(start, 10, prices=prices, volumes=volumes)
    vwap, n, warn = compute_vwap(quotes, start, start + timedelta(minutes=10))
    assert warn is None
    assert n == 10
    # 大量在 100，小量在 110 → VWAP 應接近 100，遠離 110
    assert vwap < 101.0
    assert vwap > 100.0


def test_compute_vwap_partial_window():
    """資料只有 7 分鐘，但區間請求 30 分鐘 → 仍回 7 分鐘的 VWAP（>= MIN_VALID_MINUTES=5）"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start, 7, prices=[100.0] * 7)
    end = start + timedelta(minutes=30)
    vwap, n, warn = compute_vwap(quotes, start, end)
    assert warn is None  # 7 >= MIN_VALID_MINUTES (5)
    assert n == 7
    assert vwap == pytest.approx(100.0, abs=0.01)


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------

def test_compute_vwap_empty_dataframe():
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    empty = _make_quotes(start, 0, prices=[], volumes=[])
    vwap, n, warn = compute_vwap(empty, start, start + timedelta(minutes=30))
    assert vwap is None
    assert warn == "no_data"


def test_compute_vwap_none_input():
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    vwap, n, warn = compute_vwap(None, start, start + timedelta(minutes=30))
    assert vwap is None
    assert warn == "no_data"


def test_compute_vwap_insufficient_data():
    """只有 3 分鐘資料 → insufficient_data warning"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start, 3, prices=[100.0, 100.5, 101.0])
    vwap, n, warn = compute_vwap(quotes, start, start + timedelta(minutes=30))
    assert vwap is None
    assert warn == "insufficient_data"
    assert n == 3


def test_compute_vwap_zero_volume():
    """全部成交量為 0（停牌）→ zero_volume warning"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start, 30, prices=[100.0] * 30, volumes=[0] * 30)
    vwap, n, warn = compute_vwap(quotes, start, start + timedelta(minutes=30))
    assert vwap is None
    assert warn == "zero_volume"


def test_compute_vwap_window_outside_data():
    """資料在 09:00–09:30，但查 10:00–10:30 → no_data"""
    start = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start, 30)
    far_start = datetime(2026, 4, 25, 10, 0, tzinfo=TW_TZ)
    vwap, n, warn = compute_vwap(quotes, far_start, far_start + timedelta(minutes=30))
    assert vwap is None
    assert warn == "no_data"


# ---------------------------------------------------------------------------
# Timezone handling
# ---------------------------------------------------------------------------

def test_compute_vwap_naive_datetime_input():
    """傳入 naive datetime 應自動視為 TW_TZ"""
    start_tw = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start_tw, 30)
    # naive datetime（沒有 tzinfo）
    naive_start = datetime(2026, 4, 25, 9, 0)
    naive_end = datetime(2026, 4, 25, 9, 30)
    vwap, n, warn = compute_vwap(quotes, naive_start, naive_end)
    assert warn is None
    assert n == 30


def test_compute_vwap_utc_input_converted():
    """傳入 UTC datetime 應正確轉換為 TW_TZ 計算"""
    # TW 09:00 = UTC 01:00
    start_tw = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    quotes = _make_quotes(start_tw, 30)
    utc_start = datetime(2026, 4, 25, 1, 0, tzinfo=timezone.utc)
    utc_end = datetime(2026, 4, 25, 1, 30, tzinfo=timezone.utc)
    vwap, n, warn = compute_vwap(quotes, utc_start, utc_end)
    assert warn is None
    assert n == 30


# ---------------------------------------------------------------------------
# compute_vwap_for_trigger
# ---------------------------------------------------------------------------

def test_compute_vwap_for_trigger_0930():
    """09:30 觸發 → 應抓 09:00–09:30 的 30 分鐘"""
    on_date = datetime(2026, 4, 25, tzinfo=TW_TZ)
    start_tw = datetime(2026, 4, 25, 9, 0, tzinfo=TW_TZ)
    # 09:00–09:30 全部 100 元，09:30 之後變 200 元（不應被算到）
    quotes = pd.concat([
        _make_quotes(start_tw, 30, prices=[100.0] * 30),
        _make_quotes(start_tw + timedelta(minutes=30), 30, prices=[200.0] * 30),
    ])
    result = compute_vwap_for_trigger(
        "0050", time(9, 30), on_date=on_date, quotes_override=quotes
    )
    assert isinstance(result, VWAPResult)
    assert result.symbol == "0050"
    assert result.warning is None
    assert result.sample_count == 30
    assert result.vwap == pytest.approx(100.0, abs=0.01)
    assert result.typical_window_minutes == 30


def test_compute_vwap_for_trigger_1100():
    """11:00 觸發 → 應抓 10:30–11:00 的 30 分鐘"""
    on_date = datetime(2026, 4, 25, tzinfo=TW_TZ)
    target_start = datetime(2026, 4, 25, 10, 30, tzinfo=TW_TZ)
    quotes = _make_quotes(target_start, 30, prices=[150.0] * 30)
    result = compute_vwap_for_trigger(
        "00923", time(11, 0), on_date=on_date, quotes_override=quotes
    )
    assert result.warning is None
    assert result.vwap == pytest.approx(150.0, abs=0.01)


def test_compute_vwap_for_trigger_no_data():
    """yfinance 抓不到資料 → 應回 VWAPResult with warning='no_data'"""
    on_date = datetime(2026, 4, 25, tzinfo=TW_TZ)
    result = compute_vwap_for_trigger(
        "FAKE", time(9, 30), on_date=on_date, quotes_override=None
    )
    # quotes_override=None → 會嘗試 yfinance fetch_1m_quotes，FAKE 應失敗回 None
    # 然後 compute_vwap(None,...) → no_data
    assert result.vwap is None
    assert result.warning in ("no_data", "insufficient_data")


# ---------------------------------------------------------------------------
# is_within_trigger_window / find_active_trigger
# ---------------------------------------------------------------------------

def test_is_within_trigger_window_exact():
    now = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    assert is_within_trigger_window(now, time(9, 30)) is True


def test_is_within_trigger_window_within_tolerance():
    """09:33 仍在 09:30 的 ±5 分鐘窗口內"""
    now = datetime(2026, 4, 25, 9, 33, tzinfo=TW_TZ)
    assert is_within_trigger_window(now, time(9, 30)) is True


def test_is_within_trigger_window_outside():
    """09:36 超出 09:30 的 ±5 分鐘窗口"""
    now = datetime(2026, 4, 25, 9, 36, tzinfo=TW_TZ)
    assert is_within_trigger_window(now, time(9, 30)) is False


def test_find_active_trigger_at_buy_time():
    """09:30 應回傳 09:30"""
    now = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    assert find_active_trigger(now) == time(9, 30)


def test_find_active_trigger_at_sell_time():
    """13:15 應回傳 SELL_TRIGGER_TIME"""
    now = datetime(2026, 4, 25, 13, 15, tzinfo=TW_TZ)
    assert find_active_trigger(now) == SELL_TRIGGER_TIME


def test_find_active_trigger_idle():
    """10:00（不在任何觸發窗）應回 None"""
    now = datetime(2026, 4, 25, 10, 0, tzinfo=TW_TZ)
    assert find_active_trigger(now) is None


def test_buy_trigger_times_count():
    """確認三個買入時點：09:30 / 11:00 / 13:00"""
    assert len(BUY_TRIGGER_TIMES) == 3
    assert time(9, 30) in BUY_TRIGGER_TIMES
    assert time(11, 0) in BUY_TRIGGER_TIMES
    assert time(13, 0) in BUY_TRIGGER_TIMES


def test_sell_trigger_time_value():
    assert SELL_TRIGGER_TIME == time(13, 15)
