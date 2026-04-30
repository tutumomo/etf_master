#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

try:
    from scripts.etf_core import context
    from scripts.auto_trade import peak_tracker
except ImportError:
    from etf_core import context
    from auto_trade import peak_tracker

STATE_DIR = context.get_state_dir()
OUTPUT_NAME = "portfolio_risk_report.json"

MAX_DRAWDOWN_WARN = 0.12
MAX_DRAWDOWN_BLOCK = 0.20
PORTFOLIO_VOL_WARN = 0.25
CORRELATION_WARN = 0.85


def safe_load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default or {}


def canonicalize_symbol(symbol: str | None) -> str:
    value = (symbol or "").strip().upper()
    for suffix in (".TW", ".TWO"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def returns_from_prices(prices: list[float]) -> list[float]:
    returns = []
    for prev, cur in zip(prices, prices[1:]):
        if prev and prev > 0:
            returns.append((cur - prev) / prev)
    return returns


def annualized_volatility(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    return round(stdev(returns) * math.sqrt(252), 6)


def max_drawdown(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    peak = values[0]
    worst = 0.0
    for value in values:
        if value > peak:
            peak = value
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return round(worst, 6)


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    avg_l = mean(left)
    avg_r = mean(right)
    numerator = sum((l - avg_l) * (r - avg_r) for l, r in zip(left, right))
    denom_l = math.sqrt(sum((l - avg_l) ** 2 for l in left))
    denom_r = math.sqrt(sum((r - avg_r) ** 2 for r in right))
    if denom_l == 0 or denom_r == 0:
        return None
    return round(numerator / (denom_l * denom_r), 6)


def extract_close_series(market_intelligence: dict) -> dict[str, dict[str, float]]:
    series: dict[str, dict[str, float]] = {}
    for symbol, item in (market_intelligence.get("intelligence") or {}).items():
        canonical = canonicalize_symbol(symbol)
        rows = item.get("history_30d") or []
        points = {}
        for row in rows:
            ts = row.get("t")
            close = row.get("c")
            if ts and close is not None:
                points[str(ts)[:10]] = float(close)
        if points:
            series[canonical] = points
    return series


def build_portfolio_value_series(positions: list[dict], close_series: dict[str, dict[str, float]]) -> list[dict]:
    active_positions = [
        {"symbol": canonicalize_symbol(p.get("symbol")), "quantity": float(p.get("quantity") or 0)}
        for p in positions
        if float(p.get("quantity") or 0) > 0 and canonicalize_symbol(p.get("symbol")) in close_series
    ]
    if not active_positions:
        return []

    common_dates = None
    for position in active_positions:
        dates = set(close_series[position["symbol"]].keys())
        common_dates = dates if common_dates is None else common_dates & dates
    if not common_dates:
        return []

    values = []
    for date_key in sorted(common_dates):
        value = 0.0
        for position in active_positions:
            value += position["quantity"] * close_series[position["symbol"]][date_key]
        values.append({"date": date_key, "value": round(value, 4)})
    return values


def build_symbol_risk(close_series: dict[str, dict[str, float]]) -> dict[str, dict]:
    output = {}
    for symbol, points in close_series.items():
        prices = [points[k] for k in sorted(points.keys())]
        returns = returns_from_prices(prices)
        output[symbol] = {
            "volatility_annualized": annualized_volatility(returns),
            "max_drawdown": max_drawdown(prices),
            "sample_days": len(prices),
        }
    return output


def build_correlation_pairs(close_series: dict[str, dict[str, float]]) -> list[dict]:
    symbols = sorted(close_series.keys())
    pairs = []
    for i, left in enumerate(symbols):
        for right in symbols[i + 1:]:
            common_dates = sorted(set(close_series[left].keys()) & set(close_series[right].keys()))
            left_returns = returns_from_prices([close_series[left][d] for d in common_dates])
            right_returns = returns_from_prices([close_series[right][d] for d in common_dates])
            corr = correlation(left_returns, right_returns)
            if corr is not None:
                pairs.append({"symbols": [left, right], "correlation": corr, "sample_returns": len(left_returns)})
    pairs.sort(key=lambda item: abs(float(item["correlation"])), reverse=True)
    return pairs


def build_trailing_alignment_report(tracker: dict) -> dict:
    mismatches = []
    for symbol, entry in tracker.items():
        peak = float(entry.get("peak_close") or 0)
        trailing_pct = float(entry.get("trailing_pct") or 0)
        actual_stop = float(entry.get("stop_price") or 0)
        expected_stop = peak_tracker.calc_stop_price(peak, trailing_pct) if peak > 0 else 0.0
        if round(actual_stop, 4) != expected_stop:
            mismatches.append({
                "symbol": canonicalize_symbol(symbol),
                "actual_stop": actual_stop,
                "expected_stop": expected_stop,
                "trailing_pct": trailing_pct,
            })
    return {"ok": not mismatches, "mismatches": mismatches}


def build_portfolio_risk_report(state_dir: Path) -> dict[str, Any]:
    positions_payload = safe_load_json(state_dir / "positions.json", {"positions": []})
    market_intelligence = safe_load_json(state_dir / "market_intelligence.json", {"intelligence": {}})
    tracker = safe_load_json(state_dir / "position_peak_tracker.json", {})

    positions = positions_payload.get("positions") or []
    close_series = extract_close_series(market_intelligence)
    portfolio_series = build_portfolio_value_series(positions, close_series)
    portfolio_values = [row["value"] for row in portfolio_series]
    portfolio_returns = returns_from_prices(portfolio_values)
    drawdown = max_drawdown(portfolio_values)
    volatility = annualized_volatility(portfolio_returns)
    correlation_pairs = build_correlation_pairs(close_series)
    trailing_alignment = build_trailing_alignment_report(tracker)

    warnings = []
    blockers = []
    if drawdown is not None:
        if drawdown >= MAX_DRAWDOWN_BLOCK:
            blockers.append("max_drawdown_block")
        elif drawdown >= MAX_DRAWDOWN_WARN:
            warnings.append("max_drawdown_warning")
    if volatility is not None and volatility >= PORTFOLIO_VOL_WARN:
        warnings.append("portfolio_volatility_warning")

    high_corr = [pair for pair in correlation_pairs if abs(float(pair["correlation"])) >= CORRELATION_WARN]
    if high_corr:
        warnings.append("high_correlation_warning")
    if not trailing_alignment["ok"]:
        warnings.append("trailing_stop_alignment_mismatch")

    return {
        "ok": not blockers,
        "block_buy": bool(blockers),
        "blockers": blockers,
        "warnings": warnings,
        "portfolio": {
            "max_drawdown": drawdown,
            "volatility_annualized": volatility,
            "sample_days": len(portfolio_series),
        },
        "symbols": build_symbol_risk(close_series),
        "correlation": {
            "top_pairs": correlation_pairs[:10],
            "high_correlation_pairs": high_corr[:10],
        },
        "trailing_alignment": trailing_alignment,
        "updated_at": datetime.now().isoformat(),
        "source": "portfolio_risk_report",
    }


def refresh_portfolio_risk_report(state_dir: Path = STATE_DIR, output_name: str = OUTPUT_NAME) -> dict:
    report = build_portfolio_risk_report(state_dir)
    (state_dir / output_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def build_brief(report: dict) -> str:
    portfolio = report.get("portfolio") or {}
    drawdown = portfolio.get("max_drawdown")
    volatility = portfolio.get("volatility_annualized")
    dd_text = "N/A" if drawdown is None else f"{float(drawdown) * 100:.1f}%"
    vol_text = "N/A" if volatility is None else f"{float(volatility) * 100:.1f}%"
    if report.get("block_buy"):
        return f"組合風控：阻擋買入；最大回撤 {dd_text}，年化波動 {vol_text}。"
    return f"組合風控：可買入；最大回撤 {dd_text}，年化波動 {vol_text}，warnings {len(report.get('warnings') or [])}。"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build ETF_TW portfolio-level risk report.")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="State directory")
    parser.add_argument("--json", action="store_true", help="Print full JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = refresh_portfolio_risk_report(Path(args.state_dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(build_brief(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
