#!/usr/bin/env python3
"""
buy_scanner.py — 09:30 / 11:00 / 13:00 三個時點的買入訊號掃描

策略（依使用者選擇 D1=A, D3=遵守紅線, D4=C, D5=C）：

  1. 全市場過濾（circuit_breaker）：risk-off / 重大事件 / sensor 失效 → 整體跳過
  2. 對每檔 watchlist + 持倉標的：
     a. 計算「該時點前 30 分鐘 VWAP」（D4=C）
     b. 跌幅 = (VWAP - 昨收) / 昨收
     c. 若跌幅 > -1% → 跳過此檔
     d. 依跌幅階梯決定買入金額（金額單位，不是股數）
     e. 計算股數：金額 / 即時價（無條件捨去到零股）
     f. 走 pre_flight_gate.check_order() 做完整紅線檢查
     g. 通過 → 進 pending queue
     h. 失敗 → 寫 history (status='gate_blocked')，不進 queue

  D5=C：不做策略對齊過濾，所有 watchlist 標的都掃。
  D3：同一檔同日多時點皆可進 queue，由 safety_redlines 守門。

階梯（金額為 TWD）：
  跌 1.0–1.9%  → 2,000
  跌 2.0–2.9%  → 4,000
  跌 3.0–3.9%  → 6,000
  跌 4.0–4.9%  → 8,000
  跌 ≥5.0%     → 10,000
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

import pandas as pd

ETF_TW_ROOT = Path(__file__).resolve().parents[2]
if str(ETF_TW_ROOT) not in sys.path:
    sys.path.append(str(ETF_TW_ROOT))

from scripts.etf_core import context as ctx_mod
from scripts.etf_core.state_io import safe_load_json
import scripts.pre_flight_gate as pre_flight
from scripts.auto_trade import pending_queue
from scripts.auto_trade.vwap_calculator import (
    BUY_TRIGGER_TIMES,
    TW_TZ,
    VWAPResult,
    compute_vwap_for_trigger,
)

# ---------------------------------------------------------------------------
# 跌幅階梯（金額 TWD）
# ---------------------------------------------------------------------------

DROP_LADDER: list[tuple[float, int]] = [
    # (max_drop_pct_inclusive, amount_twd)
    # 跌 1.0% 含以上、< 2.0% → 2000；以此類推
    (-1.0, 2000),
    (-2.0, 4000),
    (-3.0, 6000),
    (-4.0, 8000),
    (-5.0, 10000),  # ≥ 5% 都用 10000
]

# 觸發最小跌幅（負值表示「跌至少這個百分比」）
MIN_DROP_TO_TRIGGER = -1.0

STRATEGY_GROUP_MULTIPLIER: dict[str, dict[str, float]] = {
    "平衡配置": {"core": 1.0, "income": 1.0, "defensive": 0.5, "growth": 0.5, "smart_beta": 0.5, "other": 1.0},
    "核心累積": {"core": 1.0, "income": 0.5, "defensive": 0.5, "growth": 0.5, "smart_beta": 0.5, "other": 1.0},
    "收益優先": {"income": 1.0, "core": 0.5, "defensive": 0.5, "growth": 0.3, "smart_beta": 0.5, "other": 1.0},
    "防守保守": {"defensive": 1.0, "income": 0.5, "core": 0.3, "growth": 0.0, "smart_beta": 0.3, "other": 1.0},
    "觀察模式": {"core": 0.0, "income": 0.0, "defensive": 0.0, "growth": 0.0, "smart_beta": 0.0, "other": 0.0},
}

OVERLAY_GROUP_MULTIPLIER: dict[str, dict[str, float]] = {
    "逢低觀察": {"core": 1.0, "income": 1.0, "defensive": 1.0, "growth": 1.0, "smart_beta": 1.0, "other": 1.0},
    "高波動警戒": {"core": 0.75, "income": 0.75, "defensive": 1.0, "growth": 0.3, "smart_beta": 0.5, "other": 0.5},
    "減碼保守": {"core": 0.5, "income": 0.5, "defensive": 1.0, "growth": 0.0, "smart_beta": 0.3, "other": 0.3},
    "收益再投資": {"income": 1.25, "core": 0.75, "defensive": 0.75, "growth": 0.5, "smart_beta": 0.75, "other": 0.5},
    "無": {},
}

RISK_TEMPERATURE_MULTIPLIER = {
    "low": 1.0,
    "normal": 1.0,
    "medium": 0.9,
    "elevated": 0.5,
    "high": 0.35,
    "extreme": 0.2,
}

CAUTIOUS_GROWTH_MIN_DROP = -3.0


def ladder_amount(drop_pct: float) -> int:
    """
    依跌幅決定買入金額。drop_pct 為負值代表跌幅。
    例：drop_pct=-2.5 → 4000（落在 -2.0 ~ -3.0 區間）
    若 drop_pct > MIN_DROP_TO_TRIGGER（沒跌夠 1%）→ 0
    """
    drop_pct = round(drop_pct, 6)
    if drop_pct > MIN_DROP_TO_TRIGGER:
        return 0
    # 從最劇烈往最溫和找
    for threshold, amount in reversed(DROP_LADDER):
        if drop_pct <= threshold:
            return amount
    return 0


# ---------------------------------------------------------------------------
# 資料來源輔助
# ---------------------------------------------------------------------------

def _load_intraday_quotes(state_dir: Path) -> dict:
    return safe_load_json(state_dir / "intraday_quotes_1m.json", default={})


def _build_quotes_df(bars: list[dict]) -> pd.DataFrame | None:
    if not bars:
        return None
    idx = pd.DatetimeIndex([pd.Timestamp(b["t"]) for b in bars])
    df = pd.DataFrame({
        "Open":   [b["open"] for b in bars],
        "High":   [b["high"] for b in bars],
        "Low":    [b["low"] for b in bars],
        "Close":  [b["close"] for b in bars],
        "Volume": [b["volume"] for b in bars],
    }, index=idx)
    return df


def _get_tracked_symbols(state_dir: Path) -> list[str]:
    """讀 watchlist + positions，回傳所有需要掃描的標的。"""
    symbols: set[str] = set()
    for fname in ("watchlist.json", "positions.json"):
        data = safe_load_json(state_dir / fname, default={})
        items = data.get("items") or data.get("positions") or data.get("watchlist") or []
        for item in items:
            sym = str(item.get("symbol", "")).strip().upper()
            if sym:
                # 移除後綴
                for suffix in (".TW", ".TWO"):
                    if sym.endswith(suffix):
                        sym = sym[:-len(suffix)]
                symbols.add(sym)
    return sorted(symbols)


def _get_symbol_groups(state_dir: Path) -> dict[str, str]:
    """讀 watchlist，回傳 symbol → group 對應。"""
    data = safe_load_json(state_dir / "watchlist.json", default={})
    items = data.get("items") or data.get("watchlist") or []
    groups: dict[str, str] = {}
    for item in items:
        sym = str(item.get("symbol", "")).strip().upper()
        if not sym:
            continue
        for suffix in (".TW", ".TWO"):
            if sym.endswith(suffix):
                sym = sym[:-len(suffix)]
        groups[sym] = str(item.get("group") or item.get("category") or "other").strip().lower()
    return groups


def _get_active_cooldown(state_dir: Path, symbol: str, now: datetime) -> dict | None:
    """Return active post-sell cooldown entry for symbol, if still in force."""
    data = safe_load_json(state_dir / "position_cooldown.json", default={})
    entry = data.get(symbol.upper()) if isinstance(data, dict) else None
    if not isinstance(entry, dict):
        return None

    cooldown_until = entry.get("cooldown_until")
    if not cooldown_until:
        return None

    try:
        until_dt = datetime.fromisoformat(cooldown_until)
        if until_dt.tzinfo is None and now.tzinfo is not None:
            until_dt = until_dt.replace(tzinfo=now.tzinfo)
    except ValueError:
        return None

    if now < until_dt:
        return entry
    return None


def _load_strategy_link(state_dir: Path) -> dict:
    return safe_load_json(state_dir / "strategy_link.json", default={})


def _load_market_context(state_dir: Path) -> dict:
    context = safe_load_json(state_dir / "market_context_taiwan.json", default={})
    event_context = safe_load_json(state_dir / "market_event_context.json", default={})
    return {**event_context, **context}


def _phase2_buy_adjustment(
    *,
    base_amount: int,
    drop_pct: float,
    group: str,
    strategy: dict,
    market_context: dict,
) -> dict:
    """Calculate Phase 2 strategy-aware amount adjustment without bypassing redlines."""
    group = (group or "other").lower()
    base_strategy = strategy.get("base_strategy") or "平衡配置"
    scenario_overlay = strategy.get("scenario_overlay") or "無"
    market_regime = str(market_context.get("market_regime") or market_context.get("event_regime") or "").lower()
    risk_temperature = str(market_context.get("risk_temperature") or "normal").lower()
    defensive_tilt = str(market_context.get("defensive_tilt") or "").lower()

    strategy_multiplier = STRATEGY_GROUP_MULTIPLIER.get(base_strategy, STRATEGY_GROUP_MULTIPLIER["平衡配置"]).get(group, 0.5)
    overlay_multiplier = OVERLAY_GROUP_MULTIPLIER.get(scenario_overlay, {}).get(group, 1.0)
    risk_multiplier = RISK_TEMPERATURE_MULTIPLIER.get(risk_temperature, 1.0)
    defensive_boost = 1.25 if group == "defensive" and defensive_tilt == "high" else 1.0

    threshold_note = ""
    if group in {"growth", "smart_beta"} and (
        "cautious" in market_regime or risk_temperature in {"elevated", "high", "extreme"}
    ):
        if drop_pct > CAUTIOUS_GROWTH_MIN_DROP:
            return {
                "blocked": True,
                "block_reason": "cautious_growth_threshold",
                "base_strategy": base_strategy,
                "scenario_overlay": scenario_overlay,
                "group": group,
                "base_ladder_amount": base_amount,
                "final_amount": 0,
                "strategy_multiplier": strategy_multiplier,
                "overlay_multiplier": overlay_multiplier,
                "risk_multiplier": risk_multiplier,
                "defensive_boost": defensive_boost,
                "market_regime": market_regime,
                "risk_temperature": risk_temperature,
                "threshold_note": f"{group} 在謹慎/高風險情境需跌至 {CAUTIOUS_GROWTH_MIN_DROP:.0f}% 以上",
            }
        threshold_note = f"{group} 已符合謹慎情境加嚴門檻"

    final_multiplier = strategy_multiplier * overlay_multiplier * risk_multiplier * defensive_boost
    final_amount = int(base_amount * final_multiplier)

    if final_amount <= 0:
        return {
            "blocked": True,
            "block_reason": "strategy_disabled",
            "base_strategy": base_strategy,
            "scenario_overlay": scenario_overlay,
            "group": group,
            "base_ladder_amount": base_amount,
            "final_amount": 0,
            "strategy_multiplier": strategy_multiplier,
            "overlay_multiplier": overlay_multiplier,
            "risk_multiplier": risk_multiplier,
            "defensive_boost": defensive_boost,
            "market_regime": market_regime,
            "risk_temperature": risk_temperature,
            "threshold_note": threshold_note,
        }

    return {
        "blocked": False,
        "base_strategy": base_strategy,
        "scenario_overlay": scenario_overlay,
        "group": group,
        "base_ladder_amount": base_amount,
        "final_amount": final_amount,
        "strategy_multiplier": strategy_multiplier,
        "overlay_multiplier": overlay_multiplier,
        "risk_multiplier": risk_multiplier,
        "defensive_boost": defensive_boost,
        "market_regime": market_regime,
        "risk_temperature": risk_temperature,
        "threshold_note": threshold_note,
    }


def _get_prev_close(market_cache: dict, symbol: str) -> float | None:
    quotes = market_cache.get("quotes", {}) if isinstance(market_cache, dict) else {}
    q = quotes.get(symbol) or quotes.get(symbol.upper()) or {}
    pc = q.get("prev_close")
    return float(pc) if pc else None


def _get_current_price(market_cache: dict, symbol: str, vwap: float | None) -> float | None:
    """
    優先用 market_cache 的 current_price；若沒有則 fallback 到 VWAP。
    """
    quotes = market_cache.get("quotes", {}) if isinstance(market_cache, dict) else {}
    q = quotes.get(symbol) or quotes.get(symbol.upper()) or {}
    cp = q.get("current_price")
    if cp and float(cp) > 0:
        return float(cp)
    return vwap if vwap and vwap > 0 else None


def _calc_lot_type_and_quantity(amount_twd: int, price: float) -> tuple[str, int]:
    """
    依金額算股數。優先湊整張（1000 股 = 1 lot），不夠則用零股。
    """
    if price <= 0:
        return "odd", 0
    raw_shares = int(amount_twd // price)
    if raw_shares >= 1000:
        # 湊整數張
        lots = raw_shares // 1000
        return "board", lots * 1000
    return "odd", raw_shares


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def run_buy_scan(
    *,
    trigger_time: time,
    state_dir: Path | None = None,
    on_date: datetime | None = None,
    skip_circuit_breaker: bool = False,
    intraday_override: dict | None = None,
    market_cache_override: dict | None = None,
) -> dict:
    """
    執行單一觸發時點的買入掃描。

    Args:
        trigger_time: time(9,30) / time(11,0) / time(13,0)
        state_dir: 預設使用 etf_master 的 state
        on_date: 指定日期（測試用），預設今天
        skip_circuit_breaker: 測試用，跳過熔斷檢查
        intraday_override: 測試用，直接傳入 intraday_quotes 結構
        market_cache_override: 測試用，直接傳入 market_cache 結構

    Returns:
        {
          "trigger_time": "09:30",
          "scanned_at": ISO8601,
          "skipped": str | None,           # 整體跳過原因（circuit breaker）
          "candidates": int,                # 進入評估的標的數
          "enqueued": [signal_dict, ...],   # 成功入 queue 的訊號
          "blocked": [{symbol, reason}, ...],# pre_flight_gate 擋下的
          "below_threshold": [...],          # 跌幅不足跳過
          "cooldown": [...],                 # 賣出後冷卻中跳過
          "strategy_skipped": [...],          # 策略/情境調整後跳過
          "no_data": [...],                  # 無資料跳過
        }
    """
    state_dir = state_dir or ctx_mod.get_state_dir()
    queue_path = state_dir / "pending_auto_orders.json"
    history_path = state_dir / "auto_trade_history.jsonl"

    now = on_date or datetime.now(tz=TW_TZ)
    trigger_label = trigger_time.strftime("%H:%M")
    trigger_source = f"buy_scanner_{trigger_label.replace(':', '')}"

    result: dict[str, Any] = {
        "trigger_time": trigger_label,
        "scanned_at": now.isoformat(),
        "skipped": None,
        "candidates": 0,
        "enqueued": [],
        "blocked": [],
        "below_threshold": [],
        "cooldown": [],
        "strategy_skipped": [],
        "no_data": [],
    }

    # ── Step 1: Circuit breaker ─────────────────────────────────────────
    if not skip_circuit_breaker:
        from scripts.auto_trade.circuit_breaker import evaluate_buy_allowed
        account = safe_load_json(state_dir / "account_snapshot.json", default={})
        ssc = float(account.get("settlement_safe_cash") or account.get("cash") or 0)
        cb = evaluate_buy_allowed(
            state_dir,
            settlement_safe_cash=ssc,
            queue_path=queue_path,
            history_path=history_path,
        )
        if not cb.buy_allowed:
            result["skipped"] = "circuit_breaker"
            result["circuit_breaker_reasons"] = cb.reasons
            return result

    # ── Step 2: 載入資料 ─────────────────────────────────────────────────
    intraday = intraday_override if intraday_override is not None else _load_intraday_quotes(state_dir)
    market_cache = market_cache_override if market_cache_override is not None else safe_load_json(
        state_dir / "market_cache.json", default={}
    )
    account = safe_load_json(state_dir / "account_snapshot.json", default={})
    redlines = safe_load_json(state_dir / "safety_redlines.json", default={})
    strategy = _load_strategy_link(state_dir)
    market_context = _load_market_context(state_dir)

    cash = float(account.get("cash", 0))
    ssc = float(account.get("settlement_safe_cash") or 0)
    inventory = {p.get("symbol"): p.get("quantity", 0) for p in safe_load_json(
        state_dir / "positions.json", default={}
    ).get("positions", [])}

    max_conc_pct = redlines.get("max_buy_amount_pct")
    if max_conc_pct is None or not (0 < max_conc_pct <= 1):
        max_conc_pct = 0.5
    max_single_twd = redlines.get("max_buy_amount_twd", 1_000_000.0)

    # ── Step 3: 對每檔掃描 ─────────────────────────────────────────────
    intraday_data = intraday.get("intraday", {})
    symbols = _get_tracked_symbols(state_dir)
    symbol_groups = _get_symbol_groups(state_dir)
    result["candidates"] = len(symbols)

    for symbol in symbols:
        cooldown = _get_active_cooldown(state_dir, symbol, now)
        if cooldown:
            result["cooldown"].append({
                "symbol": symbol,
                "reason": "post_sell_cooldown",
                "cooldown_until": cooldown.get("cooldown_until"),
                "sold_at": cooldown.get("sold_at"),
            })
            continue

        bars_entry = intraday_data.get(symbol)
        if not bars_entry or not bars_entry.get("bars"):
            result["no_data"].append({"symbol": symbol, "reason": "no_intraday_bars"})
            continue

        df = _build_quotes_df(bars_entry["bars"])
        vwap_res = compute_vwap_for_trigger(
            symbol, trigger_time, on_date=now, quotes_override=df
        )

        if vwap_res.warning or vwap_res.vwap is None:
            result["no_data"].append({
                "symbol": symbol,
                "reason": vwap_res.warning or "vwap_none",
                "sample_count": vwap_res.sample_count,
            })
            continue

        prev_close = _get_prev_close(market_cache, symbol)
        if not prev_close:
            result["no_data"].append({"symbol": symbol, "reason": "no_prev_close"})
            continue

        drop_pct = (vwap_res.vwap - prev_close) / prev_close * 100
        amount = ladder_amount(drop_pct)

        if amount == 0:
            result["below_threshold"].append({
                "symbol": symbol,
                "drop_pct": round(drop_pct, 3),
                "vwap": vwap_res.vwap,
                "prev_close": prev_close,
            })
            continue

        group = symbol_groups.get(symbol, "other")
        adjustment = _phase2_buy_adjustment(
            base_amount=amount,
            drop_pct=drop_pct,
            group=group,
            strategy=strategy,
            market_context=market_context,
        )
        if adjustment["blocked"]:
            result["strategy_skipped"].append({
                "symbol": symbol,
                "reason": adjustment["block_reason"],
                "drop_pct": round(drop_pct, 3),
                "group": adjustment["group"],
                "base_strategy": adjustment["base_strategy"],
                "scenario_overlay": adjustment["scenario_overlay"],
                "base_ladder_amount": amount,
                "final_amount": adjustment["final_amount"],
                "threshold_note": adjustment.get("threshold_note", ""),
            })
            continue
        amount = int(adjustment["final_amount"])

        # ── Step 4: 算股數、走 pre_flight_gate ──────────────────────────
        current_price = _get_current_price(market_cache, symbol, vwap_res.vwap)
        if not current_price:
            result["no_data"].append({"symbol": symbol, "reason": "no_current_price"})
            continue

        lot_type, quantity = _calc_lot_type_and_quantity(amount, current_price)
        if quantity <= 0:
            result["below_threshold"].append({
                "symbol": symbol,
                "drop_pct": round(drop_pct, 3),
                "amount": amount,
                "current_price": current_price,
                "reason": "amount_too_small",
            })
            continue

        order = {
            "symbol": symbol,
            "side": "buy",
            "quantity": quantity,
            "price": current_price,
            "order_type": "limit",
            "lot_type": lot_type,
        }
        gate_ctx = {
            "state_dir": state_dir,
            "cash": cash,
            "settlement_safe_cash": ssc,
            "inventory": inventory,
            "max_concentration_pct": max_conc_pct,
            "max_single_limit_twd": max_single_twd,
            "force_trading_hours": False,  # scanner 自己有觸發時間管控
        }
        gate_res = pre_flight.check_order(order, gate_ctx)
        if not gate_res.get("passed"):
            # 寫 history（status='gate_blocked'），不進 queue
            blocked_record = {
                "_event": "gate_blocked",
                "_event_at": now.isoformat(),
                "side": "buy",
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "trigger_source": trigger_source,
                "trigger_reason": (
                    f"VWAP 跌 {drop_pct:.2f}% → 階梯 {adjustment['base_ladder_amount']} TWD，"
                    f"策略/情境調整後 {amount} TWD"
                ),
                "gate_reason": gate_res.get("reason"),
                "gate_details": gate_res.get("details", {}),
                "drop_pct": round(drop_pct, 3),
                "phase2_adjustment": adjustment,
            }
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(blocked_record, ensure_ascii=False) + "\n")
            result["blocked"].append({
                "symbol": symbol,
                "reason": gate_res.get("reason"),
                "details": gate_res.get("details", {}),
                "drop_pct": round(drop_pct, 3),
            })
            continue

        # ── Step 5: 通過 → 入 queue ─────────────────────────────────────
        signal = pending_queue.enqueue(
            queue_path=queue_path,
            history_path=history_path,
            side="buy",
            symbol=symbol,
            quantity=quantity,
            price=current_price,
            order_type="limit",
            lot_type=lot_type,
            trigger_source=trigger_source,
            trigger_reason=(
                f"VWAP 跌 {drop_pct:.2f}% → 階梯 {adjustment['base_ladder_amount']} TWD，"
                f"{adjustment['base_strategy']}/{adjustment['scenario_overlay']} "
                f"群組 {adjustment['group']} 調整後 {amount} TWD"
            ),
            trigger_payload={
                "vwap": vwap_res.vwap,
                "prev_close": prev_close,
                "drop_pct": round(drop_pct, 3),
                "ladder_amount": amount,
                "base_ladder_amount": adjustment["base_ladder_amount"],
                "strategy_multiplier": adjustment["strategy_multiplier"],
                "overlay_multiplier": adjustment["overlay_multiplier"],
                "risk_multiplier": adjustment["risk_multiplier"],
                "defensive_boost": adjustment["defensive_boost"],
                "base_strategy": adjustment["base_strategy"],
                "scenario_overlay": adjustment["scenario_overlay"],
                "group": adjustment["group"],
                "market_regime": adjustment["market_regime"],
                "risk_temperature": adjustment["risk_temperature"],
                "threshold_note": adjustment["threshold_note"],
                "vwap_sample_count": vwap_res.sample_count,
                "trigger_window": f"{vwap_res.start_time}~{vwap_res.end_time}",
            },
            now=now,
        )
        result["enqueued"].append(signal)

    return result


def run_all_buy_triggers_if_active(state_dir: Path | None = None) -> list[dict]:
    """
    cron 入口：檢查當前時間是否在任何買入觸發窗，是的話執行對應掃描。
    可能同一分鐘觸發多個（不過實務上 09:30/11:00/13:00 不重疊）。
    """
    from scripts.auto_trade.vwap_calculator import is_within_trigger_window
    now = datetime.now(tz=TW_TZ)
    results: list[dict] = []
    for t in BUY_TRIGGER_TIMES:
        if is_within_trigger_window(now, t):
            res = run_buy_scan(trigger_time=t, state_dir=state_dir, on_date=now)
            results.append(res)
    return results
