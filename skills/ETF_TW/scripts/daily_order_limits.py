#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TW_TZ = ZoneInfo("Asia/Taipei")


def default_daily_order_limits(today: str | None = None) -> dict:
    current_date = today or datetime.now(TW_TZ).date().isoformat()
    return {
        "date": current_date,
        "buy_submit_count": 0,
        "sell_submit_count": 0,
        "last_updated": datetime.now(TW_TZ).isoformat(),
    }


def _atomic_save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def ensure_daily_order_limits(path: Path, today: str | None = None) -> dict:
    default_data = default_daily_order_limits(today=today)
    if not path.exists():
        _atomic_save_json(path, default_data)
        return default_data

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _atomic_save_json(path, default_data)
        return default_data

    if data.get("date") != default_data["date"]:
        _atomic_save_json(path, default_data)
        return default_data

    merged = {
        "date": data.get("date", default_data["date"]),
        "buy_submit_count": int(data.get("buy_submit_count", 0)),
        "sell_submit_count": int(data.get("sell_submit_count", 0)),
        "last_updated": data.get("last_updated", default_data["last_updated"]),
    }
    _atomic_save_json(path, merged)
    return merged


def increment_daily_submit_count(path: Path, side: str, today: str | None = None) -> dict:
    data = ensure_daily_order_limits(path, today=today)
    normalized_side = (side or "").lower()
    if normalized_side == "buy":
        data["buy_submit_count"] += 1
    elif normalized_side == "sell":
        data["sell_submit_count"] += 1
    else:
        raise ValueError(f"Unsupported submit side: {side}")
    data["last_updated"] = datetime.now(TW_TZ).isoformat()
    _atomic_save_json(path, data)
    return data
