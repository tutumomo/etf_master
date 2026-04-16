#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

TW_TZ = ZoneInfo('Asia/Taipei')
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(13, 30)


def now_tw() -> datetime:
    return datetime.now(TW_TZ)


def is_tw_market_open(dt: datetime | None = None) -> bool:
    dt = dt.astimezone(TW_TZ) if dt else now_tw()
    if dt.weekday() >= 5:
        return False
    current = dt.time().replace(second=0, microsecond=0)
    return MARKET_OPEN <= current <= MARKET_CLOSE


if __name__ == '__main__':
    print(is_tw_market_open())
