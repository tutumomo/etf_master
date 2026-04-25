#!/usr/bin/env python3
"""
sync_intraday_quotes.py — 盤中 1 分鐘報價同步

由 cron 每分鐘執行（交易時段 09:00–13:30），把所有 watchlist + 持倉
標的的當日 1m K 線寫入 state/intraday_quotes_1m.json。

供 auto_trade.buy_scanner 與 sell_scanner 在觸發時計算 VWAP / 即時價。

注意：yfinance 對台灣股市約 15 分鐘延遲，這是已知限制。
若需要真即時報價，未來可換 Shioaji。

Usage:
    AGENT_ID=etf_master .venv/bin/python3 scripts/sync_intraday_quotes.py

cron 範例：
    * 9-13 * * 1-5 cd /path/to/ETF_TW && .venv/bin/python scripts/sync_intraday_quotes.py >> /tmp/sync_intraday.log 2>&1
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))

try:
    import yfinance as yf
except ImportError:
    yf = None

from scripts.etf_core import context
from scripts.etf_core.state_io import safe_load_json
from scripts.sync_ohlcv_history import (
    canonicalize_symbol,
    get_tracked_symbols,
    load_symbol_mappings,
    build_candidate_symbols,
)

TW_TZ = ZoneInfo("Asia/Taipei")
STATE_DIR = context.get_state_dir()
INTRADAY_PATH = STATE_DIR / "intraday_quotes_1m.json"


def fetch_intraday_for_symbol(symbol: str, mappings: dict) -> tuple[list[dict], str | None]:
    """
    抓取單一標的的當日 1m 報價。

    Returns:
        (bars, ticker_used)
        bars: list of {"t": ISO8601, "open", "high", "low", "close", "volume"}
              空 list 表示無資料
        ticker_used: 實際使用的 yfinance ticker symbol（如 '00923.TW'）
    """
    candidates = build_candidate_symbols(symbol, mappings)
    for ticker_sym in candidates:
        try:
            ticker = yf.Ticker(ticker_sym)
            hist = ticker.history(period="1d", interval="1m")
            if hist is None or hist.empty:
                continue
            # tz handling
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize("UTC").tz_convert(TW_TZ)
            else:
                hist.index = hist.index.tz_convert(TW_TZ)

            bars = []
            for ts, row in hist.iterrows():
                bars.append({
                    "t": ts.isoformat(),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]) if not _is_nan(row["Volume"]) else 0,
                })
            return bars, ticker_sym
        except Exception:
            continue
    return [], None


def _is_nan(v) -> bool:
    try:
        return v != v  # NaN 不等於自己
    except Exception:
        return False


def main() -> int:
    if yf is None:
        print("ERROR: yfinance not installed")
        return 0  # do not break refresh chain

    symbols = get_tracked_symbols()
    if not symbols:
        print("WARNING: No tracked symbols found.")
        return 0

    mappings = load_symbol_mappings()

    # 包含 0050（即使不在 watchlist 也可作為大盤基準參考）
    if "0050" not in symbols:
        symbols = sorted(set(symbols) | {"0050"})

    intraday: dict[str, dict] = {}
    errors: list[str] = []

    for symbol in symbols:
        try:
            bars, ticker_used = fetch_intraday_for_symbol(symbol, mappings)
            if not bars:
                errors.append(f"{symbol}: no_intraday_data")
                continue
            intraday[symbol] = {
                "ticker_used": ticker_used,
                "bars": bars,
                "bar_count": len(bars),
                "latest_close": bars[-1]["close"],
                "latest_time": bars[-1]["t"],
            }
        except Exception as e:
            errors.append(f"{symbol}: {type(e).__name__}: {e}")

    payload = {
        "updated_at": datetime.now(tz=TW_TZ).isoformat(),
        "source": "yfinance_1m",
        "symbol_count": len(intraday),
        "intraday": intraday,
    }
    if errors:
        payload["_errors"] = errors

    INTRADAY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"INTRADAY_QUOTES_OK symbols={len(intraday)}/{len(symbols)} errors={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
