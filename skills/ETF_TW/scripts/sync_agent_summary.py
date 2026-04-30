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


def build_reconciliation_brief(reconciliation: dict) -> str:
    if not reconciliation:
        return "成交對帳狀態：尚無 filled reconciliation 報告。"
    count = int(reconciliation.get("unreconciled_count") or 0)
    if reconciliation.get("ok", True) and count == 0:
        return "成交對帳狀態：已對齊 positions。"
    symbols = reconciliation.get("unreconciled_symbols") or []
    symbol_text = "、".join(symbols) if symbols else "未知標的"
    return f"成交對帳狀態：{count} 檔尚未對齊 positions（{symbol_text}）。"


def build_decision_quality_brief(decision_quality: dict) -> str:
    if not decision_quality:
        return "決策品質：尚無週報統計。"
    chain = decision_quality.get("chain_breakdown") or {}
    tier1 = chain.get("tier1_consensus") or {}
    rule = chain.get("rule_engine") or {}
    ai = chain.get("ai_bridge") or {}

    def _rate(bucket: dict) -> str:
        rate = bucket.get("win_rate")
        if rate is None:
            return "N/A"
        return f"{float(rate) * 100:.1f}%"

    return (
        "決策品質："
        f"Tier1共識勝率 {_rate(tier1)}（樣本 {tier1.get('total', 0)}），"
        f"規則 {_rate(rule)}，AI {_rate(ai)}。"
    )


def build_data_quality_brief(data_quality: dict) -> str:
    if not data_quality:
        return "資料品質：尚無檢查報告。"
    issues = data_quality.get("issues") or []
    warnings = data_quality.get("warnings") or []
    missing = data_quality.get("missing_quote_symbols") or []
    age = (data_quality.get("freshness") or {}).get("market_cache_age_minutes")

    if data_quality.get("ok", False) and not warnings:
        age_text = f"，market_cache 約 {age:.0f} 分鐘前更新" if isinstance(age, (int, float)) else ""
        return f"資料品質：正常{age_text}。"

    missing_text = f"；缺報價：{'、'.join(missing[:5])}" if missing else ""
    return f"資料品質：issues {len(issues)}、warnings {len(warnings)}{missing_text}。"


def build_portfolio_risk_brief(portfolio_risk: dict) -> str:
    if not portfolio_risk:
        return "組合風控：尚無報告。"
    portfolio = portfolio_risk.get("portfolio") or {}
    drawdown = portfolio.get("max_drawdown")
    volatility = portfolio.get("volatility_annualized")
    dd_text = "N/A" if drawdown is None else f"{float(drawdown) * 100:.1f}%"
    vol_text = "N/A" if volatility is None else f"{float(volatility) * 100:.1f}%"
    if portfolio_risk.get("block_buy"):
        return f"組合風控：阻擋買入；最大回撤 {dd_text}，年化波動 {vol_text}。"
    return f"組合風控：可買入；最大回撤 {dd_text}，年化波動 {vol_text}，warnings {len(portfolio_risk.get('warnings') or [])}。"


def build_news_intelligence_brief(news: dict) -> str:
    if not news:
        return "新聞情報：尚無報告。"
    return (
        "新聞情報："
        f"{news.get('signal_strength', 'none')} 訊號，"
        f"風險 {news.get('risk_flagged', 0)} 則，"
        f"ETF {news.get('etf_related', 0)} 則，"
        f"AI Bridge候選={'是' if news.get('ai_bridge_candidate') else '否'}。"
    )


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
    reconciliation = load("filled_reconciliation.json")
    decision_quality = load("decision_quality_report.json")
    data_quality = load("data_quality_report.json")
    portfolio_risk = load("portfolio_risk_report.json")
    news_intelligence = load("news_intelligence_report.json")
    signals = load("agent_summary_signals.json").get("signals", []) if (STATE_DIR / "agent_summary_signals.json").exists() else []
    
    mode_label = (mode.get("effective_mode") or "unknown").upper()
    data_source = mode.get("data_score") or snapshot.get("source") or "unknown"
    
    payload = {
        "strategy_header": build_strategy_header(strategy),
        "portfolio_brief": build_portfolio_brief(snapshot),
        "watchlist_brief": build_watchlist_brief(watchlist),
        "tape_brief": build_tape_brief(tape, intel),
        "risk_brief": build_risk_brief(signals),
        "reconciliation_brief": build_reconciliation_brief(reconciliation),
        "decision_quality_brief": build_decision_quality_brief(decision_quality),
        "data_quality_brief": build_data_quality_brief(data_quality),
        "portfolio_risk_brief": build_portfolio_risk_brief(portfolio_risk),
        "news_intelligence_brief": build_news_intelligence_brief(news_intelligence),
        "decision_quality": {
            "tier1_win_rate": (decision_quality.get("chain_breakdown") or {}).get("tier1_consensus", {}).get("win_rate"),
            "rule_win_rate": (decision_quality.get("chain_breakdown") or {}).get("rule_engine", {}).get("win_rate"),
            "ai_win_rate": (decision_quality.get("chain_breakdown") or {}).get("ai_bridge", {}).get("win_rate"),
        },
        "data_quality": {
            "ok": data_quality.get("ok", False),
            "issues": data_quality.get("issues") or [],
            "warnings": data_quality.get("warnings") or [],
            "missing_quote_symbols": data_quality.get("missing_quote_symbols") or [],
        },
        "portfolio_risk": {
            "ok": portfolio_risk.get("ok", False),
            "block_buy": portfolio_risk.get("block_buy", False),
            "blockers": portfolio_risk.get("blockers") or [],
            "warnings": portfolio_risk.get("warnings") or [],
            "portfolio": portfolio_risk.get("portfolio") or {},
        },
        "news_intelligence": {
            "ok": news_intelligence.get("ok", False),
            "signal_strength": news_intelligence.get("signal_strength", "none"),
            "ai_bridge_candidate": news_intelligence.get("ai_bridge_candidate", False),
            "warnings": news_intelligence.get("warnings") or [],
        },
        "filled_reconciliation": {
            "ok": reconciliation.get("ok", True),
            "unreconciled_count": int(reconciliation.get("unreconciled_count") or 0),
            "unreconciled_symbols": reconciliation.get("unreconciled_symbols") or [],
        },
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
