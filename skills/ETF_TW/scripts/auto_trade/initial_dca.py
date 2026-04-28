"""
initial_dca.py — 初始建倉（DCA 啟動）

骨架調整 v2 引入的「啟動期分批進場」機制。
state file: instances/<agent>/state/initial_dca_state.json

設計：
  - 預設關閉（enabled=false）
  - 用戶在 dashboard 手動啟動，給定：
      * total_target_twd  — 想用多少錢做初始建倉
      * target_days       — 分幾個交易日完成
      * symbol_priority   — 哪些 symbol 優先用 DCA 預算（依序輪流，不是均分）
  - 每個交易日 buy_scanner 跑時會先呼叫 dca_should_trigger()，
    若有 budget 還沒用完且當天還沒花過，就 enqueue 一個 DCA buy 訊號
  - DCA 期間 peak_tracker 仍正常追蹤，但 trailing 邏輯**不執行**
    （由 sell_scanner 看 dca_state.dca_phase_active 自動跳過 trailing；
     這層改動留給後續 sell_scanner 同步階段）

對應計畫：docs/intelligence-roadmap/backtest-reports/2026-04-29-stress-test.md
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def _state_path(state_dir: Path) -> Path:
    return state_dir / "initial_dca_state.json"


def default_state() -> dict:
    return {
        "enabled": False,
        "total_target_twd": 0,
        "target_days": 20,
        "started_on": None,            # ISO date 字串
        "days_done": 0,
        "twd_spent": 0,
        "completed": False,
        "last_buy_date": None,
        "symbol_priority": [],          # 依序輪流
        "next_symbol_idx": 0,
    }


def load_dca_state(state_dir: Path) -> dict:
    """讀取 DCA 狀態；不存在或損壞 → 回 default_state()"""
    path = _state_path(state_dir)
    if not path.exists():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # 補齊缺欄
        merged = default_state()
        merged.update(data)
        return merged
    except Exception:
        return default_state()


def save_dca_state(state_dir: Path, state: dict) -> None:
    path = _state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_dca_phase_active(state: dict, today: Optional[date] = None) -> bool:
    """目前是否處於 DCA 建倉期（trailing 應凍結）。"""
    if not state.get("enabled"):
        return False
    if state.get("completed"):
        return False
    days_done = int(state.get("days_done", 0))
    target_days = int(state.get("target_days", 0) or 0)
    return target_days > 0 and days_done < target_days


def dca_should_trigger(
    state: dict,
    today: date,
    available_cash: float,
) -> Optional[dict]:
    """
    判斷今天是否該觸發一筆 DCA 買單。

    Returns:
        若該觸發，回傳 {amount_twd, symbol, day_index, of_total} dict
        若不該觸發，回傳 None
    """
    if not is_dca_phase_active(state, today):
        return None

    today_iso = today.isoformat() if hasattr(today, "isoformat") else str(today)
    if state.get("last_buy_date") == today_iso:
        return None  # 今天已買過

    target_days = int(state.get("target_days", 0))
    days_done = int(state.get("days_done", 0))
    total_target = float(state.get("total_target_twd", 0))
    twd_spent = float(state.get("twd_spent", 0))

    # 每日預算 = 剩餘 / 剩餘天數
    days_remaining = max(1, target_days - days_done)
    twd_remaining = max(0.0, total_target - twd_spent)
    daily_amount = twd_remaining / days_remaining

    # 受可用現金限制
    daily_amount = min(daily_amount, available_cash)
    if daily_amount < 100:  # 太小不觸發
        return None

    # 選 symbol（輪流）
    priority: list[str] = list(state.get("symbol_priority", []))
    if not priority:
        return None
    idx = int(state.get("next_symbol_idx", 0)) % len(priority)
    symbol = priority[idx]

    return {
        "amount_twd": int(daily_amount),
        "symbol": symbol,
        "day_index": days_done + 1,
        "of_total": target_days,
        "next_symbol_idx": (idx + 1) % len(priority),
    }


def record_dca_buy(state: dict, *, today: date, amount_twd: float,
                   next_symbol_idx: int) -> dict:
    """
    在 DCA 訊號被 ack/送出後呼叫，更新狀態。
    回傳更新後的 state（caller 自己 save）。
    """
    today_iso = today.isoformat() if hasattr(today, "isoformat") else str(today)
    new_state = dict(state)
    new_state["days_done"] = int(state.get("days_done", 0)) + 1
    new_state["twd_spent"] = float(state.get("twd_spent", 0)) + float(amount_twd)
    new_state["last_buy_date"] = today_iso
    new_state["next_symbol_idx"] = int(next_symbol_idx)
    if new_state["days_done"] >= int(state.get("target_days", 0)):
        new_state["completed"] = True
    return new_state


def start_dca(
    state_dir: Path,
    *,
    total_target_twd: int,
    target_days: int,
    symbol_priority: list[str],
    today: Optional[date] = None,
) -> dict:
    """從 dashboard 端啟動 DCA。寫入 state，回傳新 state。"""
    today = today or date.today()
    state = default_state()
    state.update({
        "enabled": True,
        "total_target_twd": int(total_target_twd),
        "target_days": int(target_days),
        "started_on": today.isoformat(),
        "symbol_priority": list(symbol_priority),
        "days_done": 0,
        "twd_spent": 0,
        "completed": False,
        "last_buy_date": None,
        "next_symbol_idx": 0,
    })
    save_dca_state(state_dir, state)
    return state


def stop_dca(state_dir: Path) -> dict:
    """中止 DCA — enabled=False，保留歷史欄位。"""
    state = load_dca_state(state_dir)
    state["enabled"] = False
    save_dca_state(state_dir, state)
    return state
