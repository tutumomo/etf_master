#!/usr/bin/env python3
"""
peak_tracker.py — 持倉以來收盤最高價追蹤（trailing stop 基礎）

每日收盤後（13:30+ 或 cron 定期）更新每檔持倉的 peak_close。

state 檔案：position_peak_tracker.json
{
  "00923": {
    "entry_date": "2026-04-15",         買進日（最早一筆持倉建立日）
    "tracking_start_date": "2026-04-16",  D8=B，entry+1 個交易日
    "peak_close": 35.20,                 持倉以來收盤最高價
    "peak_close_date": "2026-04-22",
    "trailing_pct": 0.05,                依群組決定的基礎百分比
    "stop_price": 33.44,                 peak_close × (1 - trailing_pct)
    "is_locked_in": false,               是否已達 +20% 鎖利
    "last_updated": "ISO8601"
  }
}

群組對應的 trailing_pct（Q2=B）：
  core: 6%   income: 5%   defensive: 4%   other: 8%
  鎖利模式（持倉報酬 ≥ 20%）：統一收緊到 3%
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

TW_TZ = ZoneInfo("Asia/Taipei")

# 群組基礎 trailing 百分比（Q2=B）
GROUP_TRAILING_PCT: dict[str, float] = {
    "core":      0.06,
    "income":    0.05,
    "defensive": 0.04,
    "other":     0.08,
}

# 鎖利模式 trailing 百分比（持倉報酬 ≥ TRAIL_LOCK_THRESHOLD 時收緊）
TRAIL_LOCK_PCT = 0.03
TRAIL_LOCK_THRESHOLD = 0.20

DEFAULT_TRAILING_PCT = 0.06  # group=未知時 fallback


def _now_iso() -> str:
    return datetime.now(tz=TW_TZ).isoformat()


def _safe_load(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


# ---------------------------------------------------------------------------
# 純函數
# ---------------------------------------------------------------------------

def get_trailing_pct(group: str, *, return_pct: float | None = None) -> float:
    """
    依群組與當前持倉報酬決定 trailing pct。

    Args:
        group: 'core' | 'income' | 'defensive' | 'other'
        return_pct: 持倉報酬率（0.15 = +15%，0.21 = +21%）。None 表示忽略鎖利

    Returns:
        小數形式的 trailing pct（0.05 = 5%）
    """
    if return_pct is not None and return_pct >= TRAIL_LOCK_THRESHOLD:
        return TRAIL_LOCK_PCT
    return GROUP_TRAILING_PCT.get((group or "").lower(), DEFAULT_TRAILING_PCT)


def calc_stop_price(peak_close: float, trailing_pct: float) -> float:
    """stop_price = peak_close × (1 - trailing_pct)"""
    return round(peak_close * (1 - trailing_pct), 4)


def is_tracking_active(tracker_entry: dict, *, today: date | None = None) -> bool:
    """
    根據 D8=B：tracking_start_date 之前不啟動 trailing stop。
    """
    today = today or datetime.now(tz=TW_TZ).date()
    start = tracker_entry.get("tracking_start_date")
    if not start:
        return False
    try:
        start_d = date.fromisoformat(start)
    except Exception:
        return False
    return today >= start_d


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def load_tracker(state_dir: Path) -> dict:
    return _safe_load(state_dir / "position_peak_tracker.json", default={})


def save_tracker(state_dir: Path, data: dict) -> None:
    path = state_dir / "position_peak_tracker.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Updaters
# ---------------------------------------------------------------------------

def upsert_position(
    tracker: dict,
    *,
    symbol: str,
    entry_date: date,
    group: str,
    today_close: float | None = None,
    today: date | None = None,
) -> dict:
    """
    新增或更新一個持倉的 tracker entry。

    若 entry 不存在 → 建立（peak_close = today_close 或 0）
    若已存在 → 不動 entry_date，但確保 trailing_pct 與 group 同步
    """
    today = today or datetime.now(tz=TW_TZ).date()
    sym = symbol.upper()
    existing = tracker.get(sym)

    if existing is None:
        tracking_start = entry_date + timedelta(days=1)  # D8=B
        trailing_pct = get_trailing_pct(group)
        peak = float(today_close) if today_close else 0.0
        peak_date = today.isoformat() if today_close else ""
        entry = {
            "entry_date": entry_date.isoformat(),
            "tracking_start_date": tracking_start.isoformat(),
            "group": group,
            "peak_close": peak,
            "peak_close_date": peak_date,
            "trailing_pct": trailing_pct,
            "stop_price": calc_stop_price(peak, trailing_pct) if peak > 0 else 0.0,
            "is_locked_in": False,
            "last_updated": _now_iso(),
        }
        tracker[sym] = entry
        return entry

    # 已存在 → 只同步 group / trailing_pct（避免 group 變動）
    if existing.get("group") != group:
        existing["group"] = group
    new_pct = get_trailing_pct(group, return_pct=None)
    if not existing.get("is_locked_in") and existing.get("trailing_pct") != new_pct:
        existing["trailing_pct"] = new_pct
        if existing.get("peak_close", 0) > 0:
            existing["stop_price"] = calc_stop_price(existing["peak_close"], new_pct)
    existing["last_updated"] = _now_iso()
    return existing


def update_close(
    tracker: dict,
    *,
    symbol: str,
    close_price: float,
    on_date: date | None = None,
    return_pct: float | None = None,
) -> dict | None:
    """
    用「當日收盤價」更新指定持倉的 peak_close。

    流程：
      1. 若 close > peak_close → 更新 peak_close + peak_close_date
      2. 檢查是否進入鎖利模式（return_pct ≥ 20% 收緊到 3%）
      3. 重算 stop_price

    Returns:
        更新後的 entry，若該 symbol 不在 tracker 則 None
    """
    sym = symbol.upper()
    entry = tracker.get(sym)
    if entry is None:
        return None

    on_date = on_date or datetime.now(tz=TW_TZ).date()

    # 1. peak update
    cur_peak = float(entry.get("peak_close") or 0)
    if close_price > cur_peak:
        entry["peak_close"] = round(float(close_price), 4)
        entry["peak_close_date"] = on_date.isoformat()

    # 2. lock-in check
    if return_pct is not None and return_pct >= TRAIL_LOCK_THRESHOLD:
        if not entry.get("is_locked_in"):
            entry["is_locked_in"] = True
        entry["trailing_pct"] = TRAIL_LOCK_PCT
    else:
        # 若已 locked in，就不退回去（鎖利不可逆，保守設計）
        if not entry.get("is_locked_in"):
            entry["trailing_pct"] = get_trailing_pct(entry.get("group", ""))

    # 3. stop price
    if entry.get("peak_close", 0) > 0:
        entry["stop_price"] = calc_stop_price(entry["peak_close"], entry["trailing_pct"])
    entry["last_updated"] = _now_iso()
    return entry


def remove_position(tracker: dict, symbol: str) -> bool:
    """賣出後從 tracker 移除（呼叫端在 sell 成交後才 call）"""
    sym = symbol.upper()
    if sym in tracker:
        del tracker[sym]
        return True
    return False


# ---------------------------------------------------------------------------
# Sync from positions + watchlist + market data
# ---------------------------------------------------------------------------

def _build_group_lookup(state_dir: Path) -> dict[str, str]:
    """從 watchlist 建立 symbol → group 對應"""
    wl = _safe_load(state_dir / "watchlist.json", default={})
    items = wl.get("items") or wl.get("watchlist") or []
    lookup = {}
    for it in items:
        sym = str(it.get("symbol", "")).upper()
        if sym:
            lookup[sym] = it.get("group", "other")
    return lookup


def sync_with_positions(
    state_dir: Path,
    *,
    today: date | None = None,
    today_close_lookup: dict[str, float] | None = None,
    return_pct_lookup: dict[str, float] | None = None,
) -> dict:
    """
    讀 positions.json + watchlist.json，同步 tracker：
      - 新持倉 → upsert
      - 已不在持倉的 symbol → remove
      - 為每個 symbol 用今日收盤更新 peak/stop

    Args:
        today_close_lookup: {symbol: close_price}
        return_pct_lookup:  {symbol: return_pct} 用於鎖利判定

    Returns:
        更新後的 tracker dict
    """
    today = today or datetime.now(tz=TW_TZ).date()
    tracker = load_tracker(state_dir)
    positions = _safe_load(state_dir / "positions.json", default={})
    pos_list = positions.get("positions", []) if isinstance(positions, dict) else []

    group_lookup = _build_group_lookup(state_dir)
    today_close_lookup = today_close_lookup or {}
    return_pct_lookup = return_pct_lookup or {}

    current_symbols: set[str] = set()
    for p in pos_list:
        sym = str(p.get("symbol", "")).upper()
        if not sym or float(p.get("quantity") or 0) <= 0:
            continue
        current_symbols.add(sym)

        # entry_date：position 有 entry_date 就用，否則用今天
        entry_d = p.get("entry_date") or p.get("created_at", "")[:10]
        try:
            entry_date_obj = date.fromisoformat(entry_d) if entry_d else today
        except Exception:
            entry_date_obj = today

        group = group_lookup.get(sym, "other")
        today_close = today_close_lookup.get(sym)

        upsert_position(
            tracker,
            symbol=sym,
            entry_date=entry_date_obj,
            group=group,
            today_close=today_close,
            today=today,
        )

        # 用今日收盤更新 peak
        if today_close:
            update_close(
                tracker,
                symbol=sym,
                close_price=today_close,
                on_date=today,
                return_pct=return_pct_lookup.get(sym),
            )

    # 清掉已賣光的標的
    for sym in list(tracker.keys()):
        if sym not in current_symbols:
            del tracker[sym]

    save_tracker(state_dir, tracker)
    return tracker
