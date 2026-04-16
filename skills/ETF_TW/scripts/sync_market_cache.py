#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ETF_TW_ROOT / "data"
SYMBOL_MAPPINGS_PATH = DATA_DIR / "symbol_mappings.json"
import sys
sys.path.append(str(ETF_TW_ROOT))
from scripts.etf_core import context

STATE_DIR = context.get_state_dir()
POSITIONS_PATH = STATE_DIR / "positions.json"
WATCHLIST_PATH = STATE_DIR / "watchlist.json"
MARKET_CACHE_PATH = STATE_DIR / "market_cache.json"


def canonicalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def get_config_watchlist() -> list[str]:
    try:
        config_path = context.get_instance_config()
        if not config_path.exists():
            return []
        config = json.loads(config_path.read_text(encoding="utf-8"))
        # Handle both flat and structured config
        return [canonicalize_symbol(s) for s in config.get("watchlist", []) if canonicalize_symbol(s)]
    except Exception as e:
        print(f"WARNING: Could not load instance config - {e}")
        return []

def ensure_watchlist_integrity(symbols: list[str]):
    """Ensure watchlist.json contains at least basic entries for all symbols in config."""
    if not WATCHLIST_PATH.exists():
        payload = {"items": [], "updated_at": datetime.now().isoformat(), "source": "auto_init"}
    else:
        payload = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))

    normalized_items = []
    seen = set()
    changed = False
    for item in payload.get("items", []):
        original_symbol = item.get("symbol")
        canonical = canonicalize_symbol(original_symbol)
        if not canonical:
            changed = True
            continue
        if canonical in seen:
            changed = True
            continue
        normalized_name = item.get("name") if item.get("name") and item.get("name") != original_symbol else canonical
        normalized_items.append({
            **item,
            "symbol": canonical,
            "name": normalized_name,
        })
        seen.add(canonical)
        if canonical != original_symbol:
            changed = True
    payload["items"] = normalized_items

    existing = {item.get("symbol") for item in payload.get("items", [])}
    for s in symbols:
        if s not in existing:
            payload["items"].append({
                "symbol": s,
                "name": s,
                "reason": "From instance_config",
                "category": "other",
                "status": "watch",
                "group": "other"
            })
            changed = True

    if changed:
        payload["updated_at"] = datetime.now().isoformat()
        payload["source"] = "auto_sync_from_config"
        WATCHLIST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def tracked_symbols() -> list[str]:
    symbols = set()
    
    # 1. Add symbols from config
    config_symbols = get_config_watchlist()
    for s in config_symbols:
        symbols.add(s)
    
    # 2. Ensure watchlist.json is updated
    if symbols:
        ensure_watchlist_integrity(list(symbols))

    # 3. Add positions
    if POSITIONS_PATH.exists():
        try:
            payload = json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
            for item in payload.get("positions", []):
                symbol = canonicalize_symbol(item.get("symbol"))
                if symbol:
                    symbols.add(symbol)
        except: pass

    # 4. Add existing watchlist (for metadata)
    if WATCHLIST_PATH.exists():
        try:
            payload = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
            for item in payload.get("items", []):
                symbol = canonicalize_symbol(item.get("symbol"))
                if symbol:
                    symbols.add(symbol)
        except: pass
        
    return sorted(list(symbols))


def build_quote_entry(symbol: str, current_price: float, source: str = "manual", 
                      attempted_symbols: list[str] | None = None,
                      open_price: float = 0.0, high: float = 0.0, low: float = 0.0,
                      prev_close: float = 0.0) -> dict:
    return {
        "symbol": symbol,
        "current_price": current_price,
        "open": open_price,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "updated_at": datetime.now().isoformat(),
        "source": source,
        "attempted_symbols": attempted_symbols or [],
    }


def load_symbol_mappings() -> dict:
    if not SYMBOL_MAPPINGS_PATH.exists():
        return {"symbols": {}, "defaults": {"yfinance_candidates": ["{symbol}.TW"]}}
    return json.loads(SYMBOL_MAPPINGS_PATH.read_text(encoding="utf-8"))


def build_candidate_symbols(symbol: str, mappings: dict) -> list[str]:
    symbol = canonicalize_symbol(symbol)
    symbol_payload = mappings.get("symbols", {}).get(symbol, {})
    candidates = symbol_payload.get("yfinance_candidates")
    if candidates:
        return candidates
    defaults = mappings.get("defaults", {}).get("yfinance_candidates", ["{symbol}.TW"])
    return [item.format(symbol=symbol) for item in defaults]


def fetch_price(symbol: str, mappings: dict, retries: int = 2) -> tuple[float, str, list[str], dict]:
    if yf is None:
        return 0.0, "unavailable", [], {}
    attempted = []
    candidates = build_candidate_symbols(symbol, mappings)
    
    for candidate in candidates:
        attempted.append(candidate)
        for attempt in range(retries + 1):
            try:
                ticker = yf.Ticker(candidate)
                
                # Fetch 5 days of history to get stable OHLC and Previous Close
                hist = ticker.history(period="5d")
                if hist.empty:
                    continue
                
                # Latest bar is for today's intraday/close
                latest = hist.iloc[-1]
                price = float(latest['Close'])
                
                extra = {
                    "open": float(latest['Open']),
                    "high": float(latest['High']),
                    "low": float(latest['Low']),
                }
                
                # Previous Close is the close of the PREVIOUS trading bar
                if len(hist) >= 2:
                    extra["prev_close"] = float(hist['Close'].iloc[-2])
                else:
                    extra["prev_close"] = price
                
                if price > 0:
                    return price, f"yfinance:{candidate}", attempted, extra
            except Exception:
                if attempt < retries:
                    import time
                    time.sleep(1)
                continue
    return 0.0, "yfinance_error", attempted, {}


def main() -> int:
    mappings = load_symbol_mappings()
    
    # 1. Load existing cache for persistence behavior
    current_cache = {}
    if MARKET_CACHE_PATH.exists():
        try:
            current_payload = json.loads(MARKET_CACHE_PATH.read_text(encoding="utf-8"))
            current_cache = current_payload.get("quotes", {})
        except Exception:
            current_cache = {}

    quotes = {}
    for symbol in tracked_symbols():
        price, source, attempted, extra = fetch_price(symbol, mappings)
        
        open_p = extra.get("open", 0.0)
        high_p = extra.get("high", 0.0)
        low_p = extra.get("low", 0.0)
        prev_p = extra.get("prev_close", 0.0)

        # 2. Persistence Fallback: If price is 0.0 (failure), check current_cache
        if price <= 0:
            existing = current_cache.get(symbol, {})
            existing_price = float(existing.get("current_price") or 0)
            if existing_price > 0:
                price = existing_price
                open_p = float(existing.get("open", 0.0))
                high_p = float(existing.get("high", 0.0))
                low_p = float(existing.get("low", 0.0))
                prev_p = float(existing.get("prev_close", 0.0))
                source = f"last_known_cache:{existing.get('source', 'unknown')}"
        
        canonical = canonicalize_symbol(symbol)
        quotes[canonical] = build_quote_entry(canonical, price, source, attempted, 
                                           open_price=open_p, high=high_p, low=low_p, prev_close=prev_p)

    payload = {
        "quotes": quotes,
        "updated_at": datetime.now().isoformat(),
        "source": "sync_market_cache",
        "mapping_registry_version": mappings.get("meta", {}).get("version"),
    }
    MARKET_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MARKET_CACHE_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
