#!/usr/bin/env python3
"""
auto_trade_scan.py — Phase 2 自動交易 cron 入口

由 cron 每分鐘執行（建議交易時段 09:00-13:30 內每分鐘觸發）。
內部判斷當前是否在以下時間窗：

  09:30 ± 5min → 買入掃描
  11:00 ± 5min → 買入掃描
  13:00 ± 5min → 買入掃描
  13:15 ± 5min → 賣出掃描

每次執行還會：
  - 跑 expire_sweep（清過期 pending）
  - 同步 peak_tracker（每日只跑一次，13:30 後）

cron 範例（macOS launchd 或 cron）：
  * 9-13 * * 1-5 cd /path/to/ETF_TW && .venv/bin/python scripts/auto_trade_scan.py >> /tmp/auto_trade_scan.log 2>&1

注意：本腳本只負責「掃描 → 入 pending queue」與「過期清理」，
真正下單仍需要使用者透過 dashboard 的「✅ 確認下單」按鈕觸發。
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

ETF_TW_ROOT = Path(__file__).resolve().parents[1]
if str(ETF_TW_ROOT) not in sys.path:
    sys.path.append(str(ETF_TW_ROOT))

from scripts.etf_core import context as ctx_mod
from scripts.etf_core.state_io import safe_load_json
from scripts.auto_trade import (
    ack_handler,
    buy_scanner,
    peak_tracker,
    sell_scanner,
)
from scripts.auto_trade.vwap_calculator import (
    BUY_TRIGGER_TIMES,
    SELL_TRIGGER_TIME,
    TW_TZ,
    is_within_trigger_window,
)


def _now() -> datetime:
    return datetime.now(tz=TW_TZ)


def _log(msg: str) -> None:
    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _build_close_lookup_from_intraday(state_dir: Path) -> dict[str, float]:
    """從 intraday_quotes_1m.json 取每檔的 latest_close 給 peak_tracker 用"""
    intraday = safe_load_json(state_dir / "intraday_quotes_1m.json", default={})
    lookup = {}
    for sym, entry in (intraday.get("intraday") or {}).items():
        latest = entry.get("latest_close")
        if latest:
            lookup[sym.upper()] = float(latest)
    return lookup


def _build_return_pct_lookup(state_dir: Path, close_lookup: dict[str, float]) -> dict[str, float]:
    """用 positions.average_cost + 即時價算 return_pct（給鎖利判定用）"""
    positions = safe_load_json(state_dir / "positions.json", default={})
    out: dict[str, float] = {}
    for p in positions.get("positions", []):
        sym = str(p.get("symbol", "")).upper()
        avg = float(p.get("average_cost") or p.get("avg_cost") or 0)
        if not sym or avg <= 0:
            continue
        cur = close_lookup.get(sym)
        if cur:
            out[sym] = (cur - avg) / avg
    return out


def main() -> int:
    state_dir = ctx_mod.get_state_dir()
    now = _now()
    actions: list[str] = []

    # 1. 過期清理（每次都跑）
    expired = ack_handler.expire_sweep(state_dir)
    if expired:
        actions.append(f"expired={len(expired)}")

    # 2. 買入掃描
    for trigger in BUY_TRIGGER_TIMES:
        if is_within_trigger_window(now, trigger):
            label = trigger.strftime("%H:%M")
            try:
                res = buy_scanner.run_buy_scan(
                    trigger_time=trigger,
                    state_dir=state_dir,
                    on_date=now,
                )
                if res.get("skipped"):
                    actions.append(f"buy_{label}=skipped({res['skipped']})")
                else:
                    actions.append(
                        f"buy_{label}=enqueued:{len(res['enqueued'])} "
                        f"blocked:{len(res['blocked'])} below:{len(res['below_threshold'])}"
                    )
            except Exception as e:
                actions.append(f"buy_{label}=ERROR:{type(e).__name__}:{e}")

    # 3. 賣出掃描
    if is_within_trigger_window(now, SELL_TRIGGER_TIME):
        try:
            res = sell_scanner.run_sell_scan(state_dir=state_dir, on_date=now)
            actions.append(
                f"sell_1315=enqueued:{len(res['enqueued'])} "
                f"blocked:{len(res['blocked'])} above:{len(res['above_stop'])}"
            )
        except Exception as e:
            actions.append(f"sell_1315=ERROR:{type(e).__name__}:{e}")

    # 4. peak_tracker 每日同步（13:30 後一次性，避免重複）
    if now.hour == 13 and now.minute >= 30 and now.minute <= 35:
        try:
            close_lookup = _build_close_lookup_from_intraday(state_dir)
            return_pct_lookup = _build_return_pct_lookup(state_dir, close_lookup)
            tracker = peak_tracker.sync_with_positions(
                state_dir,
                today=now.date(),
                today_close_lookup=close_lookup,
                return_pct_lookup=return_pct_lookup,
            )
            actions.append(f"peak_sync=updated:{len(tracker)}")
        except Exception as e:
            actions.append(f"peak_sync=ERROR:{type(e).__name__}:{e}")

    # 5. 輸出（給 cron log 用）
    if actions:
        _log("auto_trade_scan: " + " | ".join(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
