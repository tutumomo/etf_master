#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime


def _naive_weekday_time_status(now: datetime) -> dict:
    weekday = now.weekday()  # Mon=0
    hhmm = now.hour * 100 + now.minute
    is_open = weekday < 5 and 900 <= hhmm <= 1330
    return {
        "date": now.date().isoformat(),
        "is_open": is_open,
        "session": "trading_day" if is_open else "closed",
        "reason": "weekday_time_fallback",
        "source": "weekday_time_fallback",
    }


def get_today_market_status(now: datetime, calendar_payload: dict | None = None) -> dict:
    calendar_payload = calendar_payload or {}
    dates = calendar_payload.get("dates", {})
    date_key = now.date().isoformat()
    day = dates.get(date_key)
    if day:
        return {
            "date": date_key,
            "is_open": bool(day.get("is_open")),
            "session": day.get("session") or ("trading_day" if day.get("is_open") else "closed"),
            "reason": day.get("reason") or "market_calendar_tw",
            "source": "market_calendar_tw",
        }
    return _naive_weekday_time_status(now)


def is_tw_market_open_now(now: datetime, calendar_payload: dict | None = None) -> bool:
    return bool(get_today_market_status(now=now, calendar_payload=calendar_payload).get("is_open"))
