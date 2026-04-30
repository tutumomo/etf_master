#!/usr/bin/env python3
"""
sell_scanner.py — 13:15 trailing stop 賣出訊號掃描

策略：
  1. 對每檔持倉（quantity > 0）：
     a. 檢查 tracking_start_date 是否已到（D8=B：entry+1）
     b. 取 stop_price = peak_close × (1 - trailing_pct)
     c. 取 13:15 即時價（intraday 最新 close）
     d. 若 current_price < stop_price → 觸發
     e. 走 pre_flight_gate（庫存、單位）
     f. 通過 → 入 pending queue（order_type='market'，D7）

注意：賣出訊號**不受 circuit breaker 阻擋**（保護資金更重要）。
但 sensor_health 與 master switch 仍會被檢查作為日誌警告。

賣出後 cooldown_until 寫入 position_cooldown.json，給 buy_scanner 讀。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

ETF_TW_ROOT = Path(__file__).resolve().parents[2]
if str(ETF_TW_ROOT) not in sys.path:
    sys.path.append(str(ETF_TW_ROOT))

from scripts.etf_core import context as ctx_mod
from scripts.etf_core.state_io import safe_load_json
import scripts.pre_flight_gate as pre_flight
from scripts.auto_trade import pending_queue, peak_tracker
from scripts.auto_trade.initial_dca import is_dca_phase_active, load_dca_state
from scripts.auto_trade.momentum_signals import (
    compute_relative_momentum,
    is_momentum_reversal,
)
from scripts.auto_trade.vwap_calculator import SELL_TRIGGER_TIME, TW_TZ

# 賣出後該檔多少天內不可重新買入（避免 churning）
SELL_COOLDOWN_DAYS = 7
DCA_COMPLETION_TRAILING_GRACE_DAYS = 3


def _safe_load(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _compute_market_momentum_baseline(intelligence: dict) -> float | None:
    """
    從 market_intelligence 計算大盤 20 日報酬基準（watchlist 全標的中位數）。
    當作大盤 baseline 給 momentum reversal 用。

    Returns:
        中位數（小數，例如 0.05 表示 +5%）；無資料 → None
    """
    if not isinstance(intelligence, dict):
        return None
    intel_data = intelligence.get("intelligence") or intelligence
    if not isinstance(intel_data, dict):
        return None

    momentums: list[float] = []
    for sym, data in intel_data.items():
        if not isinstance(data, dict):
            continue
        m = data.get("momentum_20d")
        if isinstance(m, (int, float)):
            momentums.append(float(m) / 100.0)  # 百分比 → 小數
    if len(momentums) < 3:
        return None
    momentums.sort()
    n = len(momentums)
    if n % 2 == 1:
        return momentums[n // 2]
    return (momentums[n // 2 - 1] + momentums[n // 2]) / 2.0


def _get_symbol_momentum_and_rsi(intelligence: dict, symbol: str) -> tuple[float | None, float | None]:
    """從 market_intelligence 取個股 momentum_20d (小數) 與 rsi。"""
    if not isinstance(intelligence, dict):
        return None, None
    intel_data = intelligence.get("intelligence") or intelligence
    if not isinstance(intel_data, dict):
        return None, None
    data = intel_data.get(symbol) or intel_data.get(symbol.upper())
    if not isinstance(data, dict):
        return None, None
    m = data.get("momentum_20d")
    r = data.get("rsi")
    momentum = float(m) / 100.0 if isinstance(m, (int, float)) else None
    rsi = float(r) if isinstance(r, (int, float)) else None
    return momentum, rsi


def _now() -> datetime:
    return datetime.now(tz=TW_TZ)


def _get_latest_close(intraday: dict, symbol: str) -> float | None:
    """從 intraday_quotes_1m.json 取最新 close。"""
    data = intraday.get("intraday", {}) if isinstance(intraday, dict) else {}
    entry = data.get(symbol) or data.get(symbol.upper())
    if not entry:
        return None
    bars = entry.get("bars", [])
    if not bars:
        return None
    return float(bars[-1].get("close") or 0) or None


def _get_market_cache_price(market_cache: dict, symbol: str) -> float | None:
    """fallback 來源：market_cache.json 的 current_price。"""
    quotes = market_cache.get("quotes", {}) if isinstance(market_cache, dict) else {}
    q = quotes.get(symbol) or quotes.get(symbol.upper())
    if not q:
        return None
    cp = q.get("current_price")
    return float(cp) if cp and float(cp) > 0 else None


def _calc_return_pct(holding: dict, current_price: float) -> float | None:
    """從持倉 avg_cost + 當前價算未實現報酬率"""
    avg = float(holding.get("average_cost") or holding.get("avg_cost") or 0)
    if avg <= 0:
        return None
    return (current_price - avg) / avg


def _is_dca_completion_grace_active(dca_state: dict, today) -> bool:
    if not dca_state.get("enabled") or not dca_state.get("completed"):
        return False
    last_buy_date = dca_state.get("last_buy_date")
    if not last_buy_date:
        return False
    try:
        completed_on = datetime.fromisoformat(str(last_buy_date)).date()
    except ValueError:
        return False
    return 0 <= (today - completed_on).days < DCA_COMPLETION_TRAILING_GRACE_DAYS


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

def write_sell_cooldown(state_dir: Path, symbol: str, *, sold_on: datetime | None = None) -> None:
    """賣出後寫入 cooldown，買入掃描會讀此檔。"""
    sold_on = sold_on or _now()
    cooldown_until = sold_on + timedelta(days=SELL_COOLDOWN_DAYS)
    path = state_dir / "position_cooldown.json"
    data = _safe_load(path, default={})
    data[symbol.upper()] = {
        "sold_at": sold_on.isoformat(),
        "cooldown_until": cooldown_until.isoformat(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def run_sell_scan(
    *,
    state_dir: Path | None = None,
    on_date: datetime | None = None,
    intraday_override: dict | None = None,
    market_cache_override: dict | None = None,
    positions_override: dict | None = None,
    tracker_override: dict | None = None,
) -> dict:
    """
    執行賣出掃描（13:15 觸發）。

    Returns:
      {
        "scanned_at": ISO8601,
        "checked": int,
        "enqueued": [signal_dict, ...],
        "blocked": [...],
        "below_stop": [...],         # 跌破 stop 但 gate 擋下的
        "above_stop": [...],          # 還沒跌破
        "dca_trailing_frozen": [...], # DCA 建倉期，trailing 凍結
        "tracking_not_started": [...],# 持倉未滿一日
        "no_data": [...],
      }
    """
    state_dir = state_dir or ctx_mod.get_state_dir()
    queue_path = state_dir / "pending_auto_orders.json"
    history_path = state_dir / "auto_trade_history.jsonl"

    now = on_date or _now()
    today = now.date()

    intraday = intraday_override if intraday_override is not None else _safe_load(
        state_dir / "intraday_quotes_1m.json", default={}
    )
    market_cache = market_cache_override if market_cache_override is not None else _safe_load(
        state_dir / "market_cache.json", default={}
    )
    positions = positions_override if positions_override is not None else _safe_load(
        state_dir / "positions.json", default={}
    )
    tracker = tracker_override if tracker_override is not None else peak_tracker.load_tracker(state_dir)

    pos_list = positions.get("positions", []) if isinstance(positions, dict) else []

    result: dict[str, Any] = {
        "scanned_at": now.isoformat(),
        "checked": 0,
        "enqueued": [],
        "blocked": [],
        "below_stop": [],
        "above_stop": [],
        "dca_trailing_frozen": [],
        "tracking_not_started": [],
        "momentum_reversed": [],   # F1: 動能反轉觸發但 gate 擋下
        "no_data": [],
    }
    dca_state = load_dca_state(state_dir)
    dca_active = is_dca_phase_active(dca_state, today=today)
    dca_grace_active = _is_dca_completion_grace_active(dca_state, today)

    # F1: 載入 market_intelligence + 計算大盤 baseline
    intelligence = _safe_load(state_dir / "market_intelligence.json", default={})
    market_baseline_20d = _compute_market_momentum_baseline(intelligence)

    inventory_lookup = {
        str(p.get("symbol", "")).upper(): float(p.get("quantity") or 0)
        for p in pos_list
    }

    for p in pos_list:
        sym = str(p.get("symbol", "")).upper()
        qty = float(p.get("quantity") or 0)
        if not sym or qty <= 0:
            continue
        result["checked"] += 1

        entry = tracker.get(sym)
        if entry is None:
            # 首次出現，沒有 tracker，無法判斷 → 略過
            result["tracking_not_started"].append({
                "symbol": sym,
                "reason": "no_tracker_entry",
            })
            continue

        # D8=B: 持倉次日才開始追蹤
        if not peak_tracker.is_tracking_active(entry, today=today):
            result["tracking_not_started"].append({
                "symbol": sym,
                "tracking_start_date": entry.get("tracking_start_date"),
                "today": today.isoformat(),
            })
            continue

        if dca_active:
            result["dca_trailing_frozen"].append({
                "symbol": sym,
                "reason": "initial_dca_active",
                "days_done": dca_state.get("days_done"),
                "target_days": dca_state.get("target_days"),
            })
            continue
        if dca_grace_active:
            result["dca_trailing_frozen"].append({
                "symbol": sym,
                "reason": "initial_dca_completion_grace",
                "last_buy_date": dca_state.get("last_buy_date"),
                "grace_days": DCA_COMPLETION_TRAILING_GRACE_DAYS,
            })
            continue

        # 取即時價（intraday 最新 → fallback market_cache.current_price）
        current_price = _get_latest_close(intraday, sym) or _get_market_cache_price(market_cache, sym)
        if not current_price:
            result["no_data"].append({"symbol": sym, "reason": "no_current_price"})
            continue

        stop_price = float(entry.get("stop_price") or 0)
        peak_close = float(entry.get("peak_close") or 0)
        trailing_pct = float(entry.get("trailing_pct") or 0)

        if stop_price <= 0 or peak_close <= 0:
            result["no_data"].append({"symbol": sym, "reason": "no_peak_or_stop"})
            continue

        # F1: 動能反轉檢查（在 trailing 之前）
        # 觸發條件：個股 20d 報酬 vs 大盤 baseline 跑輸 ≥10%、且 RSI < 40
        # 觸發 → 仍走完整 sell 流程（拆 lot / gate / enqueue），但 trigger_source
        #         標記為 sell_scanner_momentum_1315
        momentum_signal = None
        if market_baseline_20d is not None:
            sym_mom, sym_rsi = _get_symbol_momentum_and_rsi(intelligence, sym)
            rel_mom = compute_relative_momentum(
                symbol_return_20d=sym_mom, market_return_20d=market_baseline_20d,
            )
            momentum_signal = is_momentum_reversal(relative_momentum=rel_mom, rsi=sym_rsi)

        # 動能反轉觸發 → 即使 current >= stop 也要賣
        # 動能未反轉 + current >= stop → above_stop（不賣）
        if not (momentum_signal and momentum_signal.triggered):
            if current_price >= stop_price:
                result["above_stop"].append({
                    "symbol": sym,
                    "current": current_price,
                    "stop": stop_price,
                    "peak": peak_close,
                })
                continue

        # ── 觸發 ────────────────────────────────────────────────────────────
        # v2 修正：若部位有混合（整張 + 零股），需拆兩筆訊號
        # 因 pre_flight_gate 規定 odd lot 必須 1-999 股，超過要走 board lot
        total_qty = int(qty)
        sell_orders: list[tuple[int, str]] = []   # [(quantity, lot_type), ...]
        if total_qty >= 1000 and total_qty % 1000 == 0:
            sell_orders.append((total_qty, "board"))
        elif total_qty < 1000:
            sell_orders.append((total_qty, "odd"))
        else:
            # mixed：先拆整張，再剩餘零股
            board_qty = (total_qty // 1000) * 1000
            odd_qty = total_qty - board_qty
            sell_orders.append((board_qty, "board"))
            if odd_qty > 0:
                sell_orders.append((odd_qty, "odd"))
        split_group_id = f"sell-{sym}-{now.strftime('%Y%m%d%H%M%S')}" if len(sell_orders) > 1 else None

        # 主訊號（第一筆，通常是整張部分）— 後續若有零股訊號跟著一起 enqueue
        sell_qty, lot_type = sell_orders[0]
        order = {
            "symbol": sym,
            "side": "sell",
            "quantity": sell_qty,
            "price": current_price,         # 即使是 market 也帶參考價供 sizing 計算
            "order_type": "market",         # D7
            "lot_type": lot_type,
        }
        gate_ctx = {
            "cash": 0,                       # sell 不檢查 cash
            "inventory": inventory_lookup,
            "force_trading_hours": False,
        }
        gate_res = pre_flight.check_order(order, gate_ctx)

        return_pct = _calc_return_pct(p, current_price)
        is_locked = entry.get("is_locked_in", False)
        # F1: 依觸發來源決定 reason 字串與 trigger_source
        if momentum_signal and momentum_signal.triggered:
            sell_trigger_source = "sell_scanner_momentum_1315"
            reason_str = (
                f"動能反轉觸發：個股 20d 跑輸大盤 {momentum_signal.relative_momentum:+.2%} "
                f"且 RSI={momentum_signal.rsi:.1f} < 40 (current={current_price:.4f})"
            )
        else:
            sell_trigger_source = "sell_scanner_1315"
            reason_str = (
                f"trailing stop 觸發：current={current_price:.4f} < stop={stop_price:.4f} "
                f"(peak={peak_close:.4f}, trail={trailing_pct:.0%}{', locked-in' if is_locked else ''})"
            )

        if not gate_res.get("passed"):
            blocked_record = {
                "_event": "gate_blocked",
                "_event_at": now.isoformat(),
                "side": "sell",
                "symbol": sym,
                "quantity": sell_qty,
                "price": current_price,
                "trigger_source": sell_trigger_source,
                "trigger_reason": reason_str,
                "gate_reason": gate_res.get("reason"),
                "gate_details": gate_res.get("details", {}),
            }
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(blocked_record, ensure_ascii=False) + "\n")
            result["blocked"].append({
                "symbol": sym,
                "reason": gate_res.get("reason"),
                "details": gate_res.get("details", {}),
            })
            continue

        signal = pending_queue.enqueue(
            queue_path=queue_path,
            history_path=history_path,
            side="sell",
            symbol=sym,
            quantity=sell_qty,
            price=current_price,
            order_type="market",
            lot_type=lot_type,
            trigger_source=sell_trigger_source,
            trigger_reason=reason_str,
            trigger_payload={
                "current_price": current_price,
                "stop_price": stop_price,
                "peak_close": peak_close,
                "trailing_pct": trailing_pct,
                "is_locked_in": is_locked,
                "return_pct": return_pct,
                "average_cost": float(p.get("average_cost") or 0),
                "split_part": "primary" if len(sell_orders) > 1 else "single",
                "split_total": len(sell_orders),
                "split_group_id": split_group_id,
                "split_total_quantity": total_qty,
                # F1: 動能反轉訊號的稽核資訊
                "momentum_relative": momentum_signal.relative_momentum if momentum_signal else None,
                "momentum_rsi": momentum_signal.rsi if momentum_signal else None,
                "momentum_triggered": bool(momentum_signal and momentum_signal.triggered),
            },
            now=now,
        )
        result["enqueued"].append(signal)

        # v2: 若是 mixed 部位，疊上零股部分（已過 gate 一次，主訊號既然能過、零股也能過）
        for extra_qty, extra_lot in sell_orders[1:]:
            extra_order = {
                "symbol": sym,
                "side": "sell",
                "quantity": extra_qty,
                "price": current_price,
                "order_type": "market",
                "lot_type": extra_lot,
            }
            extra_gate = pre_flight.check_order(extra_order, gate_ctx)
            if not extra_gate.get("passed"):
                result["blocked"].append({
                    "symbol": sym,
                    "reason": extra_gate.get("reason"),
                    "details": extra_gate.get("details", {}),
                    "split_part": "extra",
                })
                continue
            extra_signal = pending_queue.enqueue(
                queue_path=queue_path,
                history_path=history_path,
                side="sell",
                symbol=sym,
                quantity=extra_qty,
                price=current_price,
                order_type="market",
                lot_type=extra_lot,
                trigger_source=sell_trigger_source,
                trigger_reason=reason_str + f" (split:{extra_lot})",
                trigger_payload={
                    "current_price": current_price,
                    "stop_price": stop_price,
                    "peak_close": peak_close,
                    "trailing_pct": trailing_pct,
                    "is_locked_in": is_locked,
                    "return_pct": return_pct,
                    "average_cost": float(p.get("average_cost") or 0),
                    "split_part": "secondary",
                    "split_total": len(sell_orders),
                    "split_group_id": split_group_id,
                    "split_total_quantity": total_qty,
                },
                now=now,
            )
            result["enqueued"].append(extra_signal)

    return result


def run_sell_scan_if_active(state_dir: Path | None = None) -> dict | None:
    """cron 入口：當前在 13:15 ± 5 分鐘窗口內才觸發。"""
    from scripts.auto_trade.vwap_calculator import is_within_trigger_window
    now = _now()
    if not is_within_trigger_window(now, SELL_TRIGGER_TIME):
        return None
    return run_sell_scan(state_dir=state_dir, on_date=now)
