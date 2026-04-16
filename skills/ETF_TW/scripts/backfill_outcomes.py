#!/usr/bin/env python3
"""
backfill_outcomes.py — 回測三合一腳本
1. 決策去重：同日同標的同動作 = 一筆唯一決策
2. 報酬率回補：用 yfinance 抓決策日 → N日後收盤價，計算 return_pct
3. 市場情境快照：每次決策附帶當時的 market_context

產出：
  - state/decision_outcomes_dedup.jsonl（去重後的唯一決策 + 回補報酬）
  - state/decision_context_history.jsonl（每筆決策的市場情境快照）

不修改原始檔案，純增量產出。
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo

# Add scripts dir to path for etf_core imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from etf_core.state_io import safe_load_json, safe_load_jsonl, safe_append_jsonl, atomic_save_json

import yfinance as yf

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL = Path.home() / ".hermes/profiles/etf_master/skills/ETF_TW"
STATE = SKILL / "instances/etf_master/state"
TZ = ZoneInfo("Asia/Taipei")

# yfinance ticker 後綴對照：TPEx 上櫃 ETF 用 .TWO，其餘用 .TW
# 00679B 是元大美國債20+（上櫃），其餘台灣 ETF 多數上市用 .TW
TPEX_PREFIXES = {"006"}  # 上櫃 ETF 常見前綴


def resolve_yfinance_ticker(symbol: str, market_cache: dict | None = None) -> str | None:
    """從 market_cache 的 attempted_symbols 推導 yfinance ticker，或用規則推測。"""
    # 1. 優先從 market_cache 取得實際使用的 ticker
    if market_cache:
        quotes = market_cache.get("quotes", {})
        q = quotes.get(symbol, {})
        attempted = q.get("attempted_symbols", [])
        if attempted:
            return attempted[0]
        source = q.get("source", "")
        if ":" in source:
            return source.split(":", 1)[1]
    # 2. 規則推測
    prefix = symbol[:3]
    suffix = ".TWO" if prefix in TPEX_PREFIXES else ".TW"
    return symbol + suffix

EVAL_WINDOWS = {
    "1-3 trading days": 3,
    "3-5 trading days": 5,
    "1 week": 5,
    "2 weeks": 10,
    "1 month": 22,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(dt_str: str) -> datetime:
    """Parse ISO datetime string, return tz-aware in Asia/Taipei."""
    if not dt_str:
        return datetime.min.replace(tzinfo=TZ)
    # Handle various ISO formats
    dt_str = dt_str.split("+")[0].split("Z")[0]
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.replace(tzinfo=TZ)
        except ValueError:
            continue
    return datetime.min.replace(tzinfo=TZ)


# ---------------------------------------------------------------------------
# Step 1: Dedup decisions from decision_log.jsonl
# ---------------------------------------------------------------------------

def dedup_decisions(decision_log: list[dict]) -> list[dict]:
    """
    Same date + same symbol + same action → keep the LAST one (most complete).
    Returns list of unique decisions.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in decision_log:
        dt = parse_date(row.get("scanned_at", ""))
        date_key = dt.strftime("%Y-%m-%d")
        cands = row.get("top_candidates", [])
        symbol = cands[0]["symbol"] if cands else None
        action = row.get("action", "hold")
        key = f"{date_key}|{symbol}|{action}"
        groups[key].append(row)

    deduped = []
    for key, rows in groups.items():
        # Keep the one with latest scanned_at (most data)
        rows.sort(key=lambda r: parse_date(r.get("scanned_at", "")))
        best = rows[-1].copy()
        best["_dedup_key"] = key
        best["_dedup_count"] = len(rows)
        deduped.append(best)

    deduped.sort(key=lambda r: parse_date(r.get("scanned_at", "")))
    return deduped


# ---------------------------------------------------------------------------
# Step 2: Backfill return_pct using yfinance
# ---------------------------------------------------------------------------

def fetch_price_at_date(symbol: str, target_date: datetime, market_cache: dict | None = None) -> float | None:
    """Get closing price for symbol on target_date."""
    ticker_key = resolve_yfinance_ticker(symbol, market_cache)
    if not ticker_key:
        print(f"  [WARN] Cannot resolve ticker for {symbol}")
        return None

    t = yf.Ticker(ticker_key)
    start = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    h = t.history(start=start, end=end)
    if h.empty:
        return None
    return float(h["Close"].iloc[0])


def fetch_price_n_days_later(symbol: str, decision_date: datetime, n_days: int, market_cache: dict | None = None) -> float | None:
    """Get closing price N trading days after decision_date."""
    ticker_key = resolve_yfinance_ticker(symbol, market_cache)
    if not ticker_key:
        return None

    t = yf.Ticker(ticker_key)
    # Fetch a wider window to ensure we get enough trading days
    start = (decision_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (decision_date + timedelta(days=n_days * 2 + 10)).strftime("%Y-%m-%d")
    h = t.history(start=start, end=end)
    if h.empty or len(h) <= 1:
        return None

    # Filter to dates after decision_date
    future = h[h.index > decision_date]
    if len(future) < n_days:
        # Take whatever we have
        if len(future) > 0:
            return float(future["Close"].iloc[-1])
        return None

    return float(future["Close"].iloc[n_days - 1])


def backfill_return_pct(decision: dict, market_cache: dict | None = None) -> dict:
    """Add return_pct fields to a deduped decision row."""
    cands = decision.get("top_candidates", [])
    if not cands:
        decision["return_pct_3d"] = None
        decision["return_pct_5d"] = None
        decision["return_pct_10d"] = None
        return decision

    symbol = cands[0]["symbol"]
    ref_price = cands[0].get("price")
    action = decision.get("action", "")
    scanned_at = parse_date(decision.get("scanned_at", ""))

    if not ref_price or action != "buy-preview":
        decision["reference_price"] = ref_price
        decision["return_pct_3d"] = None
        decision["return_pct_5d"] = None
        decision["return_pct_10d"] = None
        return decision

    decision["reference_price"] = ref_price

    print(f"  Backfilling {symbol} ref={ref_price} date={scanned_at.date()}")

    for n_days, label in [(3, "3d"), (5, "5d"), (10, "10d")]:
        future_price = fetch_price_n_days_later(symbol, scanned_at, n_days, market_cache)
        if future_price and ref_price > 0:
            ret = round(((future_price - ref_price) / ref_price) * 100, 2)
            decision[f"return_pct_{label}"] = ret
            decision[f"future_price_{label}"] = future_price
            decision[f"future_date_{label}"] = n_days
            print(f"    {label}: future={future_price} → return={ret}%")
        else:
            decision[f"return_pct_{label}"] = None
            print(f"    {label}: no data")

    # Primary return_pct = 3-day window (matches "1-3 trading days")
    decision["return_pct"] = decision.get("return_pct_3d")

    # Classify outcome
    rp = decision.get("return_pct")
    if rp is not None:
        if rp >= 1.5:
            decision["outcome_verdict"] = "win"
        elif rp <= -1.5:
            decision["outcome_verdict"] = "loss"
        else:
            decision["outcome_verdict"] = "flat"
    else:
        decision["outcome_verdict"] = "insufficient-data"

    return decision


# ---------------------------------------------------------------------------
# Step 3: Snapshot market context per decision
# ---------------------------------------------------------------------------

def snapshot_market_context(decision: dict) -> dict | None:
    """Extract market context from decision_log row."""
    mc = decision.get("market_context")
    if mc and isinstance(mc, dict):
        return {
            "decision_id": decision.get("decision_id"),
            "scanned_at": decision.get("scanned_at"),
            "market_context_snapshot": mc,
        }
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("backfill_outcomes.py — 回測三合一")
    print("=" * 60)

    # Load source data
    decision_log = safe_load_jsonl(STATE / "decision_log.jsonl")
    print(f"\n載入 decision_log: {len(decision_log)} 筆")
    market_cache = safe_load_json(STATE / "market_cache.json", default={})
    print(f"載入 market_cache: {len(market_cache.get('quotes', {}))} 報價")

    if not decision_log:
        print("無資料可處理，結束。")
        return 0

    # --- Step 1: Dedup ---
    print(f"\n--- Step 1: 決策去重 ---")
    deduped = dedup_decisions(decision_log)
    print(f"去重前: {len(decision_log)} 筆 → 去重後: {len(deduped)} 筆")
    for d in deduped:
        key = d.get("_dedup_key", "?")
        cnt = d.get("_dedup_count", 1)
        cands = d.get("top_candidates", [])
        sym = cands[0]["symbol"] if cands else "NONE"
        act = d.get("action", "?")
        print(f"  {key}: {sym} {act} (合併 {cnt} 筆)")

    # --- Step 2: Backfill return_pct ---
    print(f"\n--- Step 2: 報酬率回補 ---")
    for d in deduped:
        backfill_return_pct(d, market_cache)

    # Write deduped + backfilled outcomes
    out_path = STATE / "decision_outcomes_dedup.jsonl"
    # Clear existing to rewrite fully (this is a derived file, not source)
    if out_path.exists():
        out_path.unlink()
    for d in deduped:
        # Clean up internal keys before writing
        out = {k: v for k, v in d.items() if not k.startswith("_dedup_")}
        safe_append_jsonl(out_path, out)
    print(f"\n寫入 {out_path.name}: {len(deduped)} 筆")

    # --- Step 3: Market context snapshots ---
    print(f"\n--- Step 3: 市場情境快照 ---")
    ctx_path = STATE / "decision_context_history.jsonl"
    if ctx_path.exists():
        ctx_path.unlink()
    has_context = 0
    for d in deduped:
        snap = snapshot_market_context(d)
        if snap:
            safe_append_jsonl(ctx_path, snap)
            has_context += 1
    print(f"寫入 {ctx_path.name}: {has_context} 筆情境快照")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("回補結果摘要：")
    wins = sum(1 for d in deduped if d.get("outcome_verdict") == "win")
    losses = sum(1 for d in deduped if d.get("outcome_verdict") == "loss")
    flats = sum(1 for d in deduped if d.get("outcome_verdict") == "flat")
    nodata = sum(1 for d in deduped if d.get("outcome_verdict") == "insufficient-data")
    has_ret = sum(1 for d in deduped if d.get("return_pct") is not None)
    print(f"  唯一決策: {len(deduped)} 筆")
    print(f"  有報酬率: {has_ret} / {len(deduped)}")
    print(f"  Verdict: win={wins}, flat={flats}, loss={losses}, no-data={nodata}")
    print(f"  情境快照: {has_context} 筆")
    print("DONE: BACKFILL_OUTCOMES_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())