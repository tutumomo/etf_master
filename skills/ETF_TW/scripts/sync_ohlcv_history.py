#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import sys

try:
    import yfinance as yf
except ImportError:
    yf = None

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

STATE_DIR = context.get_state_dir()
MARKET_INTEL_PATH = STATE_DIR / "market_intelligence.json"
POSITIONS_PATH = STATE_DIR / "positions.json"
WATCHLIST_PATH = STATE_DIR / "watchlist.json"
SYMBOL_MAPPINGS_PATH = ETF_TW_ROOT / "data" / "symbol_mappings.json"

# --- Technical Indicator Logic (from stock-info-explorer-tw) ---

def calc_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd - sig
    return macd, sig, hist

def calc_bbands(close: pd.Series, window: int = 20, n_std: float = 2.0):
    ma = close.rolling(window=window, min_periods=window).mean()
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = ma + n_std * std
    lower = ma - n_std * std
    return upper, ma, lower

def calc_momentum(close: pd.Series, window: int = 20) -> float:
    """20-day momentum: % change over window. Positive = uptrend."""
    if len(close) < window + 1:
        return 0.0
    latest = float(close.iloc[-1])
    past = float(close.iloc[-1 - window])
    if past <= 0:
        return 0.0
    return round((latest - past) / past * 100, 4)

def calc_sharpe(close: pd.Series, window: int = 30, risk_free_annual: float = 0.02) -> float:
    """30-day Sharpe ratio (annualized) using daily log returns."""
    import math
    if len(close) < window + 1:
        return 0.0
    recent = close.iloc[-(window + 1):]
    returns = recent.pct_change().dropna()
    if len(returns) < 5:
        return 0.0
    mean_daily = float(returns.mean())
    std_daily = float(returns.std())
    if std_daily == 0:
        return 0.0
    # Annualize: daily_rf ≈ (1+annual_rf)^(1/252) - 1
    daily_rf = (1 + risk_free_annual) ** (1/252) - 1
    sharpe_daily = (mean_daily - daily_rf) / std_daily
    # Annualize
    sharpe_annual = sharpe_daily * math.sqrt(252)
    return round(sharpe_annual, 4)

def calc_yield_from_close(close: pd.Series, window: int = 252) -> float | None:
    """Estimate 1-year price return from OHLCV close series.

    NOTE: This is a proxy. Real yield data comes from yfinance .info['dividendYield']
    or from watchlist yield_pct. We compute it as a fallback only.

    Uses however many days are available (min 20), annualizes to 252 days
    so that symbols with slightly fewer trading days (e.g. 243 in a year
    with extra holidays) still get a valid estimate.
    """
    available = len(close)
    if available < 20:
        return None
    # Use full available history up to `window` days
    actual_window = min(window, available - 1)
    latest = float(close.iloc[-1])
    start = float(close.iloc[-actual_window])
    if start <= 0:
        return None
    raw_return = (latest - start) / start
    # Annualize to 252 trading days so short histories are comparable
    annualized = (1 + raw_return) ** (252 / actual_window) - 1
    return round(annualized * 100, 2)

def canonicalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def get_tracked_symbols():
    symbols = set()
    for path in [POSITIONS_PATH, WATCHLIST_PATH]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data.get("positions", []) or data.get("items", [])
            for item in items:
                s = canonicalize_symbol(item.get("symbol"))
                if s:
                    symbols.add(s)
    return sorted(list(symbols))


def load_symbol_mappings() -> dict:
    if not SYMBOL_MAPPINGS_PATH.exists():
        return {}
    return json.loads(SYMBOL_MAPPINGS_PATH.read_text(encoding="utf-8"))


def build_candidate_symbols(symbol: str, mappings: dict) -> list[str]:
    symbol = canonicalize_symbol(symbol)
    symbol_payload = mappings.get("symbols", {}).get(symbol, {})
    candidates = symbol_payload.get("yfinance_candidates") or []
    if candidates:
        return candidates
    defaults = mappings.get("defaults", {}).get("yfinance_candidates") or ["{symbol}.TW"]
    return [tpl.format(symbol=symbol) for tpl in defaults]


def build_empty_intelligence_warning(symbols: list[str], intelligence: dict) -> str | None:
    if symbols and not intelligence:
        return "market_intelligence: tracked symbols exist but intelligence payload is empty"
    return None


def append_skip_reason(errors: list[dict], symbol: str, reason: str) -> None:
    errors.append({"symbol": symbol, "reason": reason})


def build_market_intelligence_payload(symbols: list[str], intelligence: dict, existing_payload: dict | None = None, errors: list[dict] | None = None) -> dict:
    existing_payload = existing_payload or {}
    errors = errors or []
    warning = build_empty_intelligence_warning(symbols, intelligence)
    if warning and existing_payload.get("intelligence"):
        return {
            "updated_at": datetime.now().isoformat(),
            "intelligence": existing_payload.get("intelligence", {}),
            "source": "sync_ohlcv_history_pro",
            "_warning": warning,
            "_stale_fallback": True,
            "_errors": errors,
        }
    payload = {
        "updated_at": datetime.now().isoformat(),
        "intelligence": intelligence,
        "source": "sync_ohlcv_history_pro",
    }
    if warning:
        payload["_warning"] = warning
    if errors:
        payload["_errors"] = errors
    return payload


def fetch_history_for_symbol(symbol: str, mappings: dict):
    candidates = build_candidate_symbols(symbol, mappings)
    last_error = None
    for ticker_sym in candidates:
        try:
            ticker = yf.Ticker(ticker_sym)
            hist = ticker.history(period="1y")
            if hist is not None and not hist.empty:
                return hist, ticker_sym
        except Exception as e:
            last_error = e
            continue
    if last_error:
        raise last_error
    return None, None


def main():
    if yf is None:
        print("ERROR: yfinance not installed")
        return 0 # Return 0 to prevent breaking the overall refresh chain

    symbols = get_tracked_symbols()
    mappings = load_symbol_mappings()
    intelligence = {}
    errors = []
    existing_payload = {}
    if MARKET_INTEL_PATH.exists():
        try:
            existing_payload = json.loads(MARKET_INTEL_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_payload = {}
    
    if not symbols:
        print("WARNING: No tracked symbols found for intelligence sync.")
        return 0

    for symbol in symbols:
        try:
            hist, ticker_sym = fetch_history_for_symbol(symbol, mappings)
            if hist is None or hist.empty:
                print(f"WARNING: No history found for {symbol}")
                append_skip_reason(errors, symbol, "no_history")
                continue

            close = hist['Close']
            if len(close) < 60:
                print(f"WARNING: Insufficient history for {symbol} (len={len(close)})")
                append_skip_reason(errors, symbol, "insufficient_history")
                continue
            
            # Indicators
            rsi = calc_rsi(close)
            macd, macd_sig, macd_hist = calc_macd(close)
            bb_upper, bb_mid, bb_lower = calc_bbands(close)
            sma5 = close.rolling(window=5).mean()
            sma20 = close.rolling(window=20).mean()
            sma60 = close.rolling(window=60).mean()

            # Latest Values
            latest_idx = close.index[-1]
            # --- TOMO 買入三原則維度 ---
            momentum_20d = calc_momentum(close, window=20)
            sharpe_30d = calc_sharpe(close, window=30)
            return_1y = calc_yield_from_close(close, window=252)

            # Build 30-day history with full OHLCV + indicator series
            history_30d = []
            for i in range(-30, 0):
                dt = close.index[i]
                o = hist['Open'].iloc[i]
                h = hist['High'].iloc[i]
                l = hist['Low'].iloc[i]
                c = close.iloc[i]
                v = hist['Volume'].iloc[i]
                entry = {
                    "t": dt.isoformat(),
                    "o": float(o) if not pd.isna(o) else None,
                    "h": float(h) if not pd.isna(h) else None,
                    "l": float(l) if not pd.isna(l) else None,
                    "c": float(c),
                    "v": float(v) if not pd.isna(v) else None,
                    "sma5": float(sma5.iloc[i]) if not pd.isna(sma5.iloc[i]) else None,
                    "sma20": float(sma20.iloc[i]) if not pd.isna(sma20.iloc[i]) else None,
                    "sma60": float(sma60.iloc[i]) if not pd.isna(sma60.iloc[i]) else None,
                }
                history_30d.append(entry)

            intelligence[symbol] = {
                "symbol": symbol,
                "last_price": float(close.iloc[-1]),
                "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0,
                "macd": float(macd.iloc[-1]),
                "macd_signal": float(macd_sig.iloc[-1]),
                "bb_upper": float(bb_upper.iloc[-1]),
                "bb_mid": float(bb_mid.iloc[-1]),
                "bb_lower": float(bb_lower.iloc[-1]),
                "sma5": float(sma5.iloc[-1]),
                "sma20": float(sma20.iloc[-1]),
                "sma60": float(sma60.iloc[-1]),
                # --- TOMO 買入三原則維度 ---
                "momentum_20d": momentum_20d,       # 動能：20日漲跌幅%，正值=上升趨勢
                "sharpe_30d": sharpe_30d,            # 風險調整報酬：30日年化夏普值
                "return_1y": return_1y,              # 過往紀錄：1年報酬率%（價格變化，不含息）
                "updated_at": latest_idx.isoformat(),
                "history_30d": history_30d,
            }
        except Exception as e:
            print(f"ERROR: Processing {symbol} failed - {e}")
            append_skip_reason(errors, symbol, f"processing_failed:{type(e).__name__}")
            continue

    payload = build_market_intelligence_payload(
        symbols=symbols,
        intelligence=intelligence,
        existing_payload=existing_payload,
        errors=errors,
    )
    
    MARKET_INTEL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MARKET_INTELLIGENCE_OK")
    return 0

if __name__ == "__main__":
    main()
