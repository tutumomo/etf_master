#!/usr/bin/env python3
from __future__ import annotations


def compare_etfs(etf1: dict, etf2: dict) -> dict:
    return {
        "left": {
            "symbol": etf1["symbol"],
            "name": etf1["name"],
            "category": etf1["category"],
            "focus": etf1["focus"],
            "distribution_frequency": etf1["distribution_frequency"],
            "expense_ratio": etf1["expense_ratio"],
            "risk_level": etf1["risk_level"],
            "suitable_for": etf1["suitable_for"],
            "summary": etf1["summary"],
        },
        "right": {
            "symbol": etf2["symbol"],
            "name": etf2["name"],
            "category": etf2["category"],
            "focus": etf2["focus"],
            "distribution_frequency": etf2["distribution_frequency"],
            "expense_ratio": etf2["expense_ratio"],
            "risk_level": etf2["risk_level"],
            "suitable_for": etf2["suitable_for"],
            "summary": etf2["summary"],
        },
        "highlights": [
            _highlight_fee(etf1, etf2),
            _highlight_distribution(etf1, etf2),
            _highlight_suitability(etf1, etf2),
        ],
    }


def _highlight_fee(etf1: dict, etf2: dict) -> str:
    fee1 = etf1["expense_ratio"]
    fee2 = etf2["expense_ratio"]
    if fee1 == fee2:
        return f"兩者費用率相同，皆為 {fee1:.2f}%。"
    lower = etf1 if fee1 < fee2 else etf2
    higher = etf2 if lower is etf1 else etf1
    return f"{lower['symbol']} 費用率較低（{lower['expense_ratio']:.2f}% vs {higher['expense_ratio']:.2f}%）。"


def _highlight_distribution(etf1: dict, etf2: dict) -> str:
    if etf1["distribution_frequency"] == etf2["distribution_frequency"]:
        return f"兩者配息頻率相同，皆為 {etf1['distribution_frequency']}。"
    return f"配息頻率不同：{etf1['symbol']} 為 {etf1['distribution_frequency']}，{etf2['symbol']} 為 {etf2['distribution_frequency']}。"


def _highlight_suitability(etf1: dict, etf2: dict) -> str:
    s1 = set(etf1["suitable_for"])
    s2 = set(etf2["suitable_for"])
    overlap = sorted(s1 & s2)
    if overlap:
        return "共同適用情境：" + ", ".join(overlap)
    return f"適用情境不同：{etf1['symbol']} 偏 {', '.join(etf1['suitable_for'])}；{etf2['symbol']} 偏 {', '.join(etf2['suitable_for'])}。"
