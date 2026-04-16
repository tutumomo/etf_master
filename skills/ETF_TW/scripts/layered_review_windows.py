#!/usr/bin/env python3
from __future__ import annotations


def get_layered_review_windows() -> list[dict]:
    return [
        {
            'name': 'early_review',
            'label': 'T+1 早期復盤',
            'offset_trading_days': 1,
        },
        {
            'name': 'short_review',
            'label': 'T+3 短期復盤',
            'offset_trading_days': 3,
        },
        {
            'name': 'mid_review',
            'label': 'T+10 中期復盤',
            'offset_trading_days': 10,
        },
    ]
