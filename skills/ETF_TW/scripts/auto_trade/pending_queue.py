#!/usr/bin/env python3
"""
pending_queue.py — 待 ack 訊號管理

由 buy_scanner / sell_scanner 入隊，由 dashboard ack_handler 出隊。

訊號狀態流：
  pending  ──ack──▶  acked   ──complete_trade──▶  executed
                            ──gate_blocked  ──▶  blocked
           ──reject─▶  rejected
           ──expire─▶  expired

state 檔案：
  pending_auto_orders.json     當前 active pending（list）
  auto_trade_history.jsonl     所有狀態變更追加記錄

每筆訊號 schema：
{
  "id": "uuid4 string",
  "side": "buy" | "sell",
  "symbol": "00923",
  "quantity": 100,
  "price": 34.39,
  "order_type": "limit" | "market",
  "lot_type": "board" | "odd",
  "trigger_source": "buy_scanner_0930" | "sell_scanner_1315",
  "trigger_reason": "VWAP 跌 2.13% (階梯 +4000 TWD)",
  "trigger_payload": {...},        # scanner 寫入的原始資料
  "created_at": "ISO8601",
  "expires_at": "ISO8601",         # 預設 created_at + 15 分鐘
  "status": "pending"
}
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

TW_TZ = ZoneInfo("Asia/Taipei")

# 訊號 ack 過期時間（D2=B：15 分鐘）
DEFAULT_TTL_MINUTES = 15

VALID_STATUSES = {
    "pending",      # 在 queue 中等待 ack
    "acked",        # 使用者按下確認
    "executed",     # complete_trade 真的下單成功
    "rejected",     # 使用者按下拒絕
    "expired",      # 超過 TTL 未 ack
    "gate_blocked", # ack 後 pre_flight_gate 才擋下
}


def _now() -> datetime:
    return datetime.now(tz=TW_TZ)


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


# ---------------------------------------------------------------------------
# Storage IO
# ---------------------------------------------------------------------------

def _load_queue(queue_path: Path) -> list[dict]:
    if not queue_path.exists():
        return []
    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        # legacy 容錯：如果存成 dict（如 {"pending": [...]}）
        return data.get("pending", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_queue(queue_path: Path, items: list[dict]) -> None:
    queue_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _append_history(history_path: Path, record: dict) -> None:
    """追加一筆 history 記錄（JSONL 格式，安全可重入）。"""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enqueue(
    *,
    queue_path: Path,
    history_path: Path,
    side: str,
    symbol: str,
    quantity: int,
    price: float,
    order_type: str = "limit",
    lot_type: str = "board",
    trigger_source: str,
    trigger_reason: str,
    trigger_payload: dict | None = None,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    now: datetime | None = None,
) -> dict:
    """
    產生新的 pending 訊號並寫入 queue + history。

    Returns:
        新增的訊號 dict（含 id 與時間戳）
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"invalid side: {side}")
    if order_type not in ("limit", "market"):
        raise ValueError(f"invalid order_type: {order_type}")

    now = now or _now()
    expires = now + timedelta(minutes=ttl_minutes)

    signal = {
        "id": str(uuid.uuid4()),
        "side": side,
        "symbol": symbol.upper(),
        "quantity": int(quantity),
        "price": float(price),
        "order_type": order_type,
        "lot_type": lot_type,
        "trigger_source": trigger_source,
        "trigger_reason": trigger_reason,
        "trigger_payload": trigger_payload or {},
        "created_at": _to_iso(now),
        "expires_at": _to_iso(expires),
        "ttl_minutes": ttl_minutes,
        "status": "pending",
    }

    items = _load_queue(queue_path)
    items.append(signal)
    _save_queue(queue_path, items)

    _append_history(history_path, {
        **signal,
        "_event": "enqueued",
        "_event_at": _to_iso(now),
    })
    return signal


def list_active(queue_path: Path, *, now: datetime | None = None) -> list[dict]:
    """
    回傳所有當前狀態為 pending 且未過期的訊號（含每筆剩餘秒數）。
    """
    now = now or _now()
    items = _load_queue(queue_path)
    active = []
    for s in items:
        if s.get("status") != "pending":
            continue
        try:
            expires = _from_iso(s["expires_at"])
        except Exception:
            continue
        if expires <= now:
            continue
        seconds_left = max(0, int((expires - now).total_seconds()))
        active.append({**s, "seconds_left": seconds_left})
    return active


def get_by_id(queue_path: Path, signal_id: str) -> dict | None:
    items = _load_queue(queue_path)
    for s in items:
        if s.get("id") == signal_id:
            return s
    return None


def update_status(
    *,
    queue_path: Path,
    history_path: Path,
    signal_id: str,
    new_status: str,
    extra: dict | None = None,
    now: datetime | None = None,
) -> dict | None:
    """
    更新 queue 中指定訊號的 status。同時 append history。

    Returns:
        更新後的 signal dict，若找不到則 None。
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {new_status}")

    now = now or _now()
    items = _load_queue(queue_path)
    target = None
    for s in items:
        if s.get("id") == signal_id:
            s["status"] = new_status
            if extra:
                s.setdefault("status_extra", {}).update(extra)
            s["status_changed_at"] = _to_iso(now)
            target = s
            break

    if target is None:
        return None

    _save_queue(queue_path, items)
    _append_history(history_path, {
        **target,
        "_event": f"status_changed_to_{new_status}",
        "_event_at": _to_iso(now),
    })
    return target


def expire_old(
    *,
    queue_path: Path,
    history_path: Path,
    now: datetime | None = None,
) -> list[str]:
    """
    將所有 status='pending' 但 expires_at <= now 的訊號標記為 expired。

    Returns:
        被 expire 的 signal id 列表
    """
    now = now or _now()
    items = _load_queue(queue_path)
    expired_ids: list[str] = []
    changed = False
    for s in items:
        if s.get("status") != "pending":
            continue
        try:
            expires = _from_iso(s["expires_at"])
        except Exception:
            continue
        if expires <= now:
            s["status"] = "expired"
            s["status_changed_at"] = _to_iso(now)
            expired_ids.append(s["id"])
            _append_history(history_path, {
                **s,
                "_event": "status_changed_to_expired",
                "_event_at": _to_iso(now),
            })
            changed = True

    if changed:
        _save_queue(queue_path, items)

    return expired_ids


def prune_terminal(
    *,
    queue_path: Path,
    keep_days: int = 7,
    now: datetime | None = None,
) -> int:
    """
    清掉 queue 中已達終局狀態（executed / rejected / expired / gate_blocked）
    且超過 keep_days 的記錄。history 永久保留，queue 只保留近期。

    Returns:
        被清掉的數量
    """
    now = now or _now()
    cutoff = now - timedelta(days=keep_days)
    items = _load_queue(queue_path)
    terminal = {"executed", "rejected", "expired", "gate_blocked"}
    kept = []
    pruned = 0
    for s in items:
        if s.get("status") in terminal:
            try:
                changed_at = _from_iso(s.get("status_changed_at") or s["created_at"])
                if changed_at < cutoff:
                    pruned += 1
                    continue
            except Exception:
                pass
        kept.append(s)
    if pruned:
        _save_queue(queue_path, kept)
    return pruned


def count_by_status(
    queue_path: Path,
    *,
    side: str | None = None,
    on_date: str | None = None,  # 'YYYY-MM-DD'
) -> dict[str, int]:
    """
    統計各狀態數量。可選擇限定 side / 日期（依 created_at）。
    供 buy_scanner 確認當日紅線額度。
    """
    items = _load_queue(queue_path)
    counts: dict[str, int] = {}
    for s in items:
        if side and s.get("side") != side:
            continue
        if on_date:
            created = (s.get("created_at") or "")[:10]
            if created != on_date:
                continue
        st = s.get("status", "unknown")
        counts[st] = counts.get(st, 0) + 1
    return counts


def sum_today_buy_amount(queue_path: Path, *, on_date: str | None = None) -> float:
    """
    當日所有 buy 訊號（pending + acked + executed）的金額總和。
    用於檢查「當日下單金額累計 ≤ 可交割金額 × 50%」紅線。
    """
    items = _load_queue(queue_path)
    on_date = on_date or _now().date().isoformat()
    counted_statuses = {"pending", "acked", "executed"}
    total = 0.0
    for s in items:
        if s.get("side") != "buy":
            continue
        if s.get("status") not in counted_statuses:
            continue
        if (s.get("created_at") or "")[:10] != on_date:
            continue
        total += float(s.get("quantity", 0)) * float(s.get("price", 0))
    return round(total, 2)
