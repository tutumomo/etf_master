#!/usr/bin/env python3
from __future__ import annotations


REPORT_TEMPLATES = {
    "morning": {
        "title": "ETF_TW 早班報告",
        "sections": ["持倉與帳戶", "市場體制判讀", "風險訊號更新", "今日觀察重點", "執行檢查"],
    },
    "post_market": {
        "title": "ETF_TW 盤後收工報告",
        "sections": ["資料同步狀態", "持倉明細與盤後診斷", "決策品質評分", "明日操作傾向", "缺口與待辦"],
    },
    "weekly": {
        "title": "ETF_TW 每週深度復盤",
        "sections": ["本週摘要", "雙鏈勝率（累計）", "本週最準確標的（Top 3）", "本週最大失誤（Top 3）", "策略一致性審計", "下週操作傾向"],
    },
}


def get_report_template(kind: str) -> dict:
    try:
        return REPORT_TEMPLATES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown report template: {kind}") from exc


def section_heading(kind: str, section: str) -> str:
    template = get_report_template(kind)
    if section not in template["sections"]:
        raise ValueError(f"section {section!r} is not in template {kind!r}")
    return f"## {section}"
