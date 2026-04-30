#!/usr/bin/env python3
"""
compute_correlation_matrix.py — 週期性更新 watchlist 的 pairwise 相關矩陣

從 yfinance 抓 watchlist 全標的過去 N 天日線，計算 pairwise 相關，
寫入 state/correlation_matrix.json，供 buy_scanner 在擬買時使用。

預設：60 天視窗（夠長到含括短期波動，又不到去抓到 regime 變化前的舊資料）。

執行頻率：每週一次（cron 或手動）

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 E2)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.etf_core import context as ctx_mod
from scripts.etf_core.state_io import safe_load_json


WINDOW_DAYS = 60
DEFAULT_PERIOD = "3mo"   # yfinance period 字串，足夠抓 60+ 個交易日


def _load_watchlist_symbols(state_dir: Path) -> list[str]:
    data = safe_load_json(state_dir / "watchlist.json", default={})
    items = data.get("items") or data.get("watchlist") or []
    syms: list[str] = []
    for item in items:
        s = str(item.get("symbol", "")).strip().upper()
        if not s:
            continue
        for sfx in (".TW", ".TWO"):
            if s.endswith(sfx):
                s = s[: -len(sfx)]
        if s and s not in syms:
            syms.append(s)
    return syms


def _yf_ticker(symbol: str) -> str:
    """裸 symbol → yfinance ticker，預設加 .TW"""
    if "." in symbol:
        return symbol
    return f"{symbol}.TW"


def fetch_returns_matrix(symbols: list[str], period: str = DEFAULT_PERIOD):
    """從 yfinance 抓所有 symbol 的日線收盤價 → 計算日報酬率 DataFrame。"""
    import pandas as pd

    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance required")

    closes: dict[str, list] = {}
    for s in symbols:
        ticker = _yf_ticker(s)
        try:
            hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
            if hist is None or len(hist) < 30:
                print(f"  WARN: {ticker} insufficient data ({0 if hist is None else len(hist)} bars)")
                continue
            closes[s] = hist["Close"].astype(float)
        except Exception as exc:
            print(f"  ERROR: {ticker}: {exc}")
            continue

    if not closes:
        return pd.DataFrame()

    # Align all series on the same date index
    df = pd.DataFrame(closes)
    df = df.dropna(how="all")
    returns = df.pct_change().dropna()
    return returns.tail(WINDOW_DAYS)


def main(argv: list[str]) -> int:
    state_dir = ctx_mod.get_state_dir()
    out_path = state_dir / "correlation_matrix.json"

    symbols = _load_watchlist_symbols(state_dir)
    if not symbols:
        print("CORR_MATRIX_SKIP: empty watchlist")
        return 0

    print(f"Fetching returns for {len(symbols)} symbols ({DEFAULT_PERIOD} window)...")
    returns = fetch_returns_matrix(symbols, period=DEFAULT_PERIOD)
    if returns.empty:
        print("CORR_MATRIX_FAIL: no returns data")
        return 1

    matrix = returns.corr()
    payload = {
        "computed_at": datetime.now().isoformat(),
        "window_days": int(WINDOW_DAYS),
        "actual_bars": int(len(returns)),
        "symbols": list(matrix.columns),
        "matrix": {
            sym_a: {sym_b: float(matrix.loc[sym_a, sym_b]) for sym_b in matrix.columns}
            for sym_a in matrix.index
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CORR_MATRIX_OK: {len(matrix.columns)} symbols × {len(returns)} bars → {out_path}")

    # 印出 high-correlation pairs（>0.85）作為人類可讀摘要
    high_corr_pairs: list[tuple[str, str, float]] = []
    syms = list(matrix.columns)
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            c = float(matrix.loc[a, b])
            if c >= 0.85:
                high_corr_pairs.append((a, b, c))
    high_corr_pairs.sort(key=lambda x: -x[2])
    if high_corr_pairs:
        print(f"\nHigh-correlation pairs (≥0.85):")
        for a, b, c in high_corr_pairs[:20]:
            print(f"  {a:8s} vs {b:8s}: {c:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
