#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()

GROUP_LABELS = {
    "core": "核心區",
    "income": "收益區",
    "defensive": "防守區",
    "other": "其他區",
}


def load_state(name: str) -> dict:
    path = STATE / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ts(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def freshness_text(updated_at: str | None) -> tuple[str, list[str]]:
    issues = []
    dt = parse_ts(updated_at)
    if not dt:
        issues.append("market_cache 缺失或時間格式無法解析")
        return "資料新鮮度：未知", issues
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    age = (now - dt).total_seconds()
    if age <= 600:
        return f"資料新鮮度：fresh（約 {int(age//60)} 分鐘前）", issues
    if age <= 3600:
        issues.append("market_cache 已超過 10 分鐘未更新")
        return f"資料新鮮度：stale（約 {int(age//60)} 分鐘前）", issues
    issues.append("market_cache 已超過 1 小時未更新")
    return f"資料新鮮度：old（約 {int(age//60)} 分鐘前）", issues


def build_summary(mode: str) -> str:
    watchlist = load_state("watchlist.json")
    market_cache = load_state("market_cache.json")
    agent_summary = load_state("agent_summary.json")
    portfolio_snapshot = load_state("portfolio_snapshot.json")

    items = watchlist.get("items", [])
    quotes = market_cache.get("quotes", {})
    grouped = defaultdict(list)
    anomalies: list[str] = []

    for item in items:
        group = item.get("group") or "other"
        symbol = item.get("symbol", "?")
        quote = quotes.get(symbol, {})
        price = quote.get("current_price")
        if price in (None, 0, ""):
            anomalies.append(f"{symbol} 缺少有效報價")
        grouped[group].append({
            "symbol": symbol,
            "name": item.get("name", symbol),
            "price": price,
            "reason": item.get("reason", ""),
        })

    for required in ("core", "income", "defensive"):
        if not grouped.get(required):
            anomalies.append(f"{GROUP_LABELS[required]} 目前為空")

    freshness_line, freshness_issues = freshness_text(market_cache.get("updated_at"))
    anomalies.extend(freshness_issues)

    concentration = portfolio_snapshot.get("largest_position_weight")
    if concentration and float(concentration) >= 60:
        anomalies.append(f"持倉集中度偏高（{float(concentration):.2f}%）")

    title = "盤前監控摘要" if mode == "am" else "盤後監控摘要"
    lines = [title]
    if agent_summary.get("portfolio_brief"):
        lines.append(agent_summary["portfolio_brief"])
    lines.append(freshness_line)
    lines.append("")

    for key in ("core", "income", "defensive"):
        lines.append(f"{GROUP_LABELS[key]}：")
        for row in grouped.get(key, []):
            price_text = f"{float(row['price']):.4f}" if row.get("price") not in (None, "") else "N/A"
            lines.append(f"- {row['symbol']} {row['name']}｜現價 {price_text}｜{row['reason']}")
        if not grouped.get(key):
            lines.append("- 暫無標的")
        lines.append("")

    if anomalies:
        lines.append("異常提醒：" + "；".join(dict.fromkeys(anomalies)))
    else:
        lines.append("目前無異常提醒")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["am", "pm"], required=True)
    args = parser.parse_args()
    print(build_summary(args.mode), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
