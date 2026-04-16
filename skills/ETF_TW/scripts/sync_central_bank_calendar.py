#!/usr/bin/env python3
"""
sync_central_bank_calendar.py — 央行會議/FOMC 日曆

由於沙盒無法連外站，使用硬編碼的已知會議日期 + 年度更新機制。
寫入 state/central_bank_calendar.json

欄位：
- upcoming: [{date, event, type, importance, days_until}]
- last_updated: ISO date
- source: 'hardcoded_2026' (未來可改為 scraping)
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from etf_core.state_io import atomic_save_json
from etf_core.state_schema import validate_state_payload
from etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
CALENDAR_PATH = STATE / 'central_bank_calendar.json'

# 2026 已知央行會議日期（FOMC 8 次/年，台灣央行 4 次/年）
FOMC_DATES_2026 = [
    # FOMC meetings: Jan, Mar, May, Jun, Jul, Sep, Oct, Dec (typical pattern)
    # 2026 exact dates TBD, using typical Wed pattern
    ('2026-01-28', 'FOMC 1月利率決策', 'high'),
    ('2026-03-18', 'FOMC 3月利率決策（含經濟預測）', 'high'),
    ('2026-05-13', 'FOMC 5月利率決策', 'medium'),
    ('2026-06-17', 'FOMC 6月利率決策（含經濟預測+點陣圖）', 'high'),
    ('2026-07-29', 'FOMC 7月利率決策', 'medium'),
    ('2026-09-16', 'FOMC 9月利率決策（含經濟預測）', 'high'),
    ('2026-10-28', 'FOMC 10月利率決策', 'medium'),
    ('2026-12-16', 'FOMC 12月利率決策（含經濟預測+點陣圖）', 'high'),
]

CBC_DATES_2026 = [
    # 台灣央行理監事會議（通常 3/6/9/12 月）
    ('2026-03-19', '台灣央行 Q1 理監事會議', 'high'),
    ('2026-06-18', '台灣央行 Q2 理監事會議', 'high'),
    ('2026-09-17', '台灣央行 Q3 理監事會議', 'high'),
    ('2026-12-17', '台灣央行 Q4 理監事會議', 'high'),
]


def sync_calendar() -> dict:
    today = date.today()
    upcoming = []

    for date_str, event, importance in FOMC_DATES_2026 + CBC_DATES_2026:
        try:
            meeting_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        days_until = (meeting_date - today).days
        if days_until < -7:  # past meetings (7 day grace)
            continue
        event_type = 'FOMC' if 'FOMC' in event else 'CBC'
        upcoming.append({
            'date': date_str,
            'event': event,
            'type': event_type,
            'importance': importance,
            'days_until': days_until,
        })

    # Sort by date
    upcoming.sort(key=lambda x: x['date'])

    # Next high-importance event
    next_major = next((e for e in upcoming if e['importance'] == 'high' and e['days_until'] >= 0), None)

    payload = {
        'upcoming': upcoming,
        'next_major': next_major,
        'total_upcoming': len(upcoming),
        'last_updated': today.isoformat(),
        'source': 'hardcoded_2026',
        'note': '日期為預估值，FOMC 確切日期以 Fed 官方公告為準',
    }

    validated = validate_state_payload('central_bank_calendar', payload, {
        'upcoming': [], 'next_major': None
    })
    atomic_save_json(CALENDAR_PATH, validated)

    next_desc = f"{next_major['event']} ({next_major['days_until']}天後)" if next_major else '無'
    print(f"CENTRAL_BANK_CALENDAR_OK: {len(upcoming)} upcoming, next major: {next_desc}")
    return validated


if __name__ == '__main__':
    sync_calendar()