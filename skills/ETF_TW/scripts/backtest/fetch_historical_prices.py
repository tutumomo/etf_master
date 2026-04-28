#!/usr/bin/env python3
"""
Fetch historical daily OHLC for backtest scenarios.

Caches to instances/<agent>/state/backtest_cache/<symbol>_<start>_<end>.parquet
to avoid hitting yfinance repeatedly during development.

Usage:
    python -m scripts.backtest.fetch_historical_prices 0050.TW 2008-01-01 2009-06-30
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

# Allow running as module or script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.etf_core import context


def cache_path(symbol: str, start: str, end: str, state_dir: Optional[Path] = None) -> Path:
    state_dir = state_dir or context.get_state_dir()
    cache_dir = state_dir / "backtest_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace(".", "_").replace("/", "_").replace("^", "_")
    return cache_dir / f"{safe_symbol}_{start}_{end}.csv"


def fetch_daily_history(
    symbol: str,
    start: str,
    end: str,
    *,
    use_cache: bool = True,
    state_dir: Optional[Path] = None,
):
    """
    Fetch daily OHLCV from yfinance with parquet caching.

    Args:
        symbol: yfinance ticker (e.g. '0050.TW', '^TWII')
        start, end: ISO date strings 'YYYY-MM-DD'
        use_cache: if True, return cached file when present
        state_dir: override state dir (for testing)

    Returns:
        pandas.DataFrame with columns Open/High/Low/Close/Volume, DatetimeIndex
        Empty DataFrame if fetch failed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas required for backtest")

    cache = cache_path(symbol, start, end, state_dir)
    if use_cache and cache.exists():
        try:
            df = pd.read_csv(cache, index_col=0, parse_dates=True)
            return df
        except Exception:
            pass

    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance required for backtest fetch")

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, auto_adjust=False)
        if df is None or len(df) == 0:
            return pd.DataFrame()
        # Normalize columns and tz
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.to_csv(cache)
        return df
    except Exception as exc:
        print(f"FETCH_ERROR {symbol} {start}→{end}: {exc}", file=sys.stderr)
        return pd.DataFrame()


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("Usage: fetch_historical_prices.py SYMBOL START END")
        return 1
    symbol, start, end = argv[1], argv[2], argv[3]
    df = fetch_daily_history(symbol, start, end)
    if len(df) == 0:
        print(f"FAILED: {symbol} {start} {end}")
        return 2
    print(f"FETCHED {symbol}: {len(df)} bars, {df.index[0].date()} → {df.index[-1].date()}")
    print(f"CACHE: {cache_path(symbol, start, end)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
