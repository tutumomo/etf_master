#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE_DIR = context.get_state_dir()
OUTPUT_PATH = STATE_DIR / "agent_summary.json"


def load(name: str) -> dict:
    path = STATE_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_strategy_header(strategy: dict) -> str:
    base = strategy.get("base_strategy") or "未設定"
    overlay = strategy.get("scenario_overlay") or "無"
    return f"[目前投資策略:{base}, 情境覆蓋:{overlay}]"


def build_portfolio_brief(snapshot: dict) -> str:
    holdings = snapshot.get("holdings", [])
    cash = snapshot.get("cash", 0)
    total_equity = snapshot.get("total_equity", 0)
    return f"目前持有 {len(holdings)} 檔標的，現金 {cash:,.0f} 元，總資產約 {total_equity:,.0f} 元。"


def canonicalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def build_watchlist_brief(watchlist: dict) -> str:
    items = watchlist.get("items", [])
    if not items:
        return "目前沒有關注標的。"
    seen = []
    for item in items:
        symbol = canonicalize_symbol(item.get("symbol"))
        if symbol and symbol not in seen:
            seen.append(symbol)
    return "目前關注標的：" + "、".join(seen[:5]) + ("。" if len(seen) <= 5 else " 等。")


def build_risk_brief(signals: list[dict]) -> list[str]:
    return [f"{s.get('title')}：{s.get('detail')}" for s in signals[:5]]


def build_tape_brief(tape: dict, intel: dict) -> str:
    bias = tape.get("market_bias") or "neutral"
    summary = tape.get("tape_summary") or "無特殊盤感摘要。"

    top_signals = []
    seen = set()
    for sym, data in intel.get("intelligence", {}).items():
        canonical = canonicalize_symbol(sym)
        if not canonical or canonical in seen:
            continue
        rsi = data.get("rsi", 50)
        ma_status = "站上月線" if data.get("last_price", 0) > data.get("sma20", 0) else "月線之下"
        top_signals.append(f"{canonical}(RSI:{rsi:.0f}, {ma_status})")
        seen.add(canonical)
        if len(top_signals) >= 3:
            break

    intel_part = " | 關鍵指標：" + "、".join(top_signals) if top_signals else ""
    return f"目前市場情緒：{bias}。{summary}{intel_part}"


def main() -> int:
    strategy = load("strategy_link.json")
    snapshot = load("portfolio_snapshot.json")
    watchlist = load("watchlist.json")
    mode = load("trading_mode.json")
    tape = load("intraday_tape_context.json")
    intel = load("market_intelligence.json")
    signals = load("agent_summary_signals.json").get("signals", []) if (STATE_DIR / "agent_summary_signals.json").exists() else []
    
    mode_label = (mode.get("effective_mode") or "unknown").upper()
    data_source = mode.get("data_score") or snapshot.get("source") or "unknown"
    
    payload = {
        "strategy_header": build_strategy_header(strategy),
        "portfolio_brief": build_portfolio_brief(snapshot),
        "watchlist_brief": build_watchlist_brief(watchlist),
        "tape_brief": build_tape_brief(tape, intel),
        "risk_brief": build_risk_brief(signals),
        "mode_brief": f"目前模式 {mode_label}，資料來源 {data_source}。",
        "updated_at": datetime.now().isoformat(),
        "source": "state_aggregator",
        "raw_mode": mode.get("effective_mode"),
        "raw_strategy": strategy.get("base_strategy")
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("AGENT_SUMMARY_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
