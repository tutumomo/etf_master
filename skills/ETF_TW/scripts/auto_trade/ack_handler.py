#!/usr/bin/env python3
"""
ack_handler.py — Dashboard ack/reject 訊號的後端處理

提供三個函式：
  ack_signal(signal_id):
    1. 查找訊號（必須 status='pending' 且未過期）
    2. 重跑 pre_flight_gate（防止 ack 時市場已劇變）
    3. 通過 → 標記 'acked' → 呼叫 complete_trade.py 真實下單
       a. 成功 → 'executed'
       b. 失敗 → 'gate_blocked'（保留下單失敗原因）
    4. 失敗 → 'gate_blocked'

  reject_signal(signal_id, reason): 純標記 rejected

  expire_sweep(): 將過期 pending 標 expired
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

ETF_TW_ROOT = Path(__file__).resolve().parents[2]
if str(ETF_TW_ROOT) not in sys.path:
    sys.path.append(str(ETF_TW_ROOT))

from scripts.etf_core import context as ctx_mod
from scripts.etf_core.state_io import safe_load_json
import scripts.pre_flight_gate as pre_flight
from scripts.auto_trade import pending_queue
from scripts.auto_trade import sell_scanner
from scripts.auto_trade.vwap_calculator import TW_TZ


def _now() -> datetime:
    return datetime.now(tz=TW_TZ)


def _state_paths(state_dir: Path):
    return {
        "queue": state_dir / "pending_auto_orders.json",
        "history": state_dir / "auto_trade_history.jsonl",
    }


def _build_gate_context(state_dir: Path, side: str) -> dict:
    """重新組裝 pre_flight_gate 需要的 context（ack 時最新狀態）。"""
    account = safe_load_json(state_dir / "account_snapshot.json", default={})
    positions_data = safe_load_json(state_dir / "positions.json", default={})
    redlines = safe_load_json(state_dir / "safety_redlines.json", default={})

    inventory = {
        str(p.get("symbol", "")).upper(): float(p.get("quantity") or 0)
        for p in positions_data.get("positions", [])
    }

    max_conc = redlines.get("max_buy_amount_pct")
    if max_conc is None or not (0 < max_conc <= 1):
        max_conc = 0.5

    return {
        "cash": float(account.get("cash") or 0),
        "settlement_safe_cash": float(account.get("settlement_safe_cash") or 0),
        "inventory": inventory,
        "max_concentration_pct": max_conc,
        "max_single_limit_twd": redlines.get("max_buy_amount_twd", 1_000_000.0),
        "force_trading_hours": True,
        "state_dir": state_dir,
    }


def expire_sweep(state_dir: Path | None = None) -> list[str]:
    """清理過期 pending（cron 每分鐘呼叫一次）"""
    state_dir = state_dir or ctx_mod.get_state_dir()
    paths = _state_paths(state_dir)
    return pending_queue.expire_old(
        queue_path=paths["queue"],
        history_path=paths["history"],
    )


def reject_signal(signal_id: str, *, reason: str = "user_rejected", state_dir: Path | None = None) -> dict | None:
    """使用者拒絕訊號"""
    state_dir = state_dir or ctx_mod.get_state_dir()
    paths = _state_paths(state_dir)
    return pending_queue.update_status(
        queue_path=paths["queue"],
        history_path=paths["history"],
        signal_id=signal_id,
        new_status="rejected",
        extra={"rejected_reason": reason},
    )


def ack_signal(
    signal_id: str,
    *,
    state_dir: Path | None = None,
    dry_run: bool = False,
    skip_complete_trade: bool = False,  # 測試用
) -> dict:
    """
    使用者按下「✅ 確認下單」。

    Returns:
        {
          "ok": bool,
          "status": "executed" | "gate_blocked" | "expired" | "not_found" | "wrong_status",
          "signal": {...},        # 更新後的訊號
          "reason": str,
          "execution_output": str # complete_trade.py 的輸出
        }
    """
    state_dir = state_dir or ctx_mod.get_state_dir()
    paths = _state_paths(state_dir)

    # 1. 查找訊號
    signal = pending_queue.get_by_id(paths["queue"], signal_id)
    if signal is None:
        return {"ok": False, "status": "not_found", "reason": f"signal {signal_id} 不存在"}

    if signal.get("status") != "pending":
        return {
            "ok": False,
            "status": "wrong_status",
            "reason": f"目前狀態是 {signal.get('status')}，不能 ack",
            "signal": signal,
        }

    # 2. 過期檢查
    try:
        expires_at = datetime.fromisoformat(signal["expires_at"])
    except Exception:
        expires_at = None
    if expires_at and expires_at <= _now():
        # 主動標 expired
        pending_queue.update_status(
            queue_path=paths["queue"], history_path=paths["history"],
            signal_id=signal_id, new_status="expired",
            extra={"expired_via": "ack_check"},
        )
        return {"ok": False, "status": "expired", "reason": "訊號已過期"}

    # 3. 重跑 pre_flight_gate
    side = signal.get("side", "")
    gate_ctx = _build_gate_context(state_dir, side)
    order = {
        "symbol": signal["symbol"],
        "side": side,
        "quantity": int(signal["quantity"]),
        "price": float(signal["price"]),
        "order_type": signal.get("order_type", "limit"),
        "lot_type": signal.get("lot_type", "board"),
        "is_submit": True,
        "is_confirmed": True,
    }
    gate_res = pre_flight.check_order(order, gate_ctx)

    if not gate_res.get("passed"):
        updated = pending_queue.update_status(
            queue_path=paths["queue"], history_path=paths["history"],
            signal_id=signal_id, new_status="gate_blocked",
            extra={
                "gate_reason": gate_res.get("reason"),
                "gate_details": gate_res.get("details", {}),
                "blocked_at_ack": True,
            },
        )
        return {
            "ok": False,
            "status": "gate_blocked",
            "reason": gate_res.get("reason"),
            "signal": updated,
            "gate_details": gate_res.get("details", {}),
        }

    # 4. 通過 → 標記 acked
    pending_queue.update_status(
        queue_path=paths["queue"], history_path=paths["history"],
        signal_id=signal_id, new_status="acked",
    )

    if dry_run:
        return {
            "ok": True,
            "status": "acked",
            "reason": "dry_run，未實際下單",
            "signal": pending_queue.get_by_id(paths["queue"], signal_id),
        }

    # 5. 真實下單
    if skip_complete_trade:
        execution_output = "[skip_complete_trade=True]"
        execution_ok = True
    else:
        execution_output, execution_ok = _invoke_complete_trade(signal, state_dir=state_dir)

    # 6. 標記終局狀態
    if execution_ok:
        final = pending_queue.update_status(
            queue_path=paths["queue"], history_path=paths["history"],
            signal_id=signal_id, new_status="executed",
            extra={"execution_output": execution_output[:500]},
        )
        # sell 訊號成交後寫 cooldown
        if side == "sell":
            sell_scanner.write_sell_cooldown(state_dir, signal["symbol"], sold_on=_now())
        return {
            "ok": True,
            "status": "executed",
            "reason": "下單成功",
            "signal": final,
            "execution_output": execution_output,
        }
    else:
        # complete_trade.py 失敗 → 標記為 gate_blocked（語意：執行階段被擋）
        final = pending_queue.update_status(
            queue_path=paths["queue"], history_path=paths["history"],
            signal_id=signal_id, new_status="gate_blocked",
            extra={
                "execution_output": execution_output[:500],
                "blocked_at_execution": True,
            },
        )
        return {
            "ok": False,
            "status": "gate_blocked",
            "reason": "complete_trade.py 失敗",
            "signal": final,
            "execution_output": execution_output,
        }


def _invoke_complete_trade(signal: dict, *, state_dir: Path | None = None) -> tuple[str, bool]:
    """
    呼叫既有的 complete_trade.py 完成下單。

    沿用 dashboard.app trade_submit 同樣的命令格式。
    """
    venv_python = ETF_TW_ROOT / ".venv" / "bin" / "python3"
    if not venv_python.exists():
        venv_python = ETF_TW_ROOT / ".venv" / "bin" / "python"

    trading_mode = safe_load_json((state_dir or ctx_mod.get_state_dir()) / "trading_mode.json", default={})
    mode = str(trading_mode.get("effective_mode") or "paper").lower()
    if mode == "live-ready":
        mode = "live"
    broker = trading_mode.get("default_broker", "sinopac")
    account = trading_mode.get("default_account", "sinopac_01")

    cmd = [
        str(venv_python),
        str(ETF_TW_ROOT / "scripts" / "complete_trade.py"),
        signal["symbol"],
        signal["side"],
        str(signal["quantity"]),
        "--price", str(signal["price"]),
        "--mode", mode,
        "--broker", broker,
        "--account", account,
        "--decision-id", signal["id"],
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ETF_TW_ROOT),
        )
        output = (proc.stdout or "") + ("\n[stderr]\n" + proc.stderr if proc.stderr else "")
        ok = proc.returncode == 0
        if ok and mode == "live":
            ok = "broker_order_id" in output or "ordno" in output or "VERIFIED" in output
        return output.strip(), ok
    except subprocess.TimeoutExpired:
        return "complete_trade.py 執行逾時（60s）", False
    except Exception as e:
        return f"complete_trade.py 執行例外：{type(e).__name__}: {e}", False
