#!/usr/bin/env python3
"""
production_replay.py — 用真實生產代碼跑歷史資料的回放驗證器

對應 B 計畫：驗證生產的 buy_scanner / peak_tracker / initial_dca / sell_scanner
能否在 2024 Bull 歷史資料上跑出**接近 simulator** 的結果。

設計：
  - 為每個交易日「製造」一個 mock state 目錄（每日重新寫 watchlist /
    market_cache / intraday_quotes / account_snapshot 等）
  - 直接呼叫 run_buy_scan / run_sell_scan / DCA 入隊邏輯
  - 訊號出來後**自動 ack**（跳過 dashboard），按收盤價成交、扣手續費
  - 累積 equity curve，與 simulator 對照

Mock 重點：
  - force_trading_hours 設 False（透過 _skip 和 ctx）
  - safety_redlines 寫一份完全允許的版本
  - circuit_breaker 用 skip_circuit_breaker=True
  - 每日的 30 個 1m bar 全部用收盤價（VWAP = close）
  - 不打 yfinance 不打券商

用法：
  AGENT_ID=etf_master PYTHONPATH=. .venv/bin/python -m scripts.backtest.production_replay
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TW_TZ = ZoneInfo("Asia/Taipei")
LOT_SIZE = 1000
BROKER_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.001


# ---------------------------------------------------------------------------
# Mock state writer
# ---------------------------------------------------------------------------

def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_intraday(symbol: str, day: date, close: float, volume: int = 1_000_000) -> dict:
    """造 09:00–09:30 的 30 個 1m bar，全用 close 價格 → VWAP = close。
       這樣 drop_pct = (VWAP - prev_close) / prev_close 就跟生產 simulator 對齊。"""
    bars = []
    base = datetime.combine(day, time(9, 0), tzinfo=TW_TZ)
    for i in range(30):
        t = base + timedelta(minutes=i)
        bars.append({
            "t": t.isoformat(),
            "open": close, "high": close, "low": close, "close": close,
            "volume": volume,
        })
    return {
        "ticker_used": f"{symbol}.TW",
        "bars": bars,
        "bar_count": 30,
        "latest_close": close,
        "latest_time": (base + timedelta(minutes=29)).isoformat(),
    }


def write_daily_state(
    state_dir: Path,
    *,
    symbol: str,
    today: date,
    close: float,
    prev_close: float,
    cash: float,
    inventory_shares: int,
    avg_cost: float,
    dca_state: dict | None = None,
    macro_regime: str = "balanced_bullish",
) -> None:
    """每日重寫所有 mock state。"""
    bare_sym = symbol.replace(".TW", "").replace(".TWO", "")

    # watchlist
    _write_json(state_dir / "watchlist.json", {
        "items": [{"symbol": bare_sym, "group": "core"}],
    })

    # positions
    positions = []
    if inventory_shares > 0:
        positions.append({
            "symbol": bare_sym,
            "quantity": inventory_shares,
            "average_cost": avg_cost,
            "entry_date": (today - timedelta(days=2)).isoformat(),
        })
    _write_json(state_dir / "positions.json", {"positions": positions})

    # intraday_quotes_1m
    _write_json(state_dir / "intraday_quotes_1m.json", {
        "intraday": {bare_sym: _make_intraday(bare_sym, today, close)},
    })

    # market_cache
    _write_json(state_dir / "market_cache.json", {
        "quotes": {
            bare_sym: {
                "current_price": close,
                "prev_close": prev_close,
                "volume_ratio": 1.0,
                "change_rate": (close - prev_close) / prev_close * 100.0 if prev_close else 0.0,
            },
        },
    })

    # account_snapshot
    _write_json(state_dir / "account_snapshot.json", {
        "cash": cash,
        "settlement_safe_cash": cash,
        "future_settlement_net_t1_t2": 0,
    })

    # safety_redlines — 開寬讓我們能驗證實際邏輯，不被紅線擋
    _write_json(state_dir / "safety_redlines.json", {
        "enabled": True,
        "max_buy_amount_pct": 0.95,
        "max_buy_amount_twd": 10_000_000,
        "max_buy_shares": 1_000_000,
        "daily_max_buy_submits": 999,
        "daily_max_sell_submits": 999,
    })

    # daily_pnl 與 daily_order_limits
    _write_json(state_dir / "daily_pnl.json", {"circuit_breaker_triggered": False})
    _write_json(state_dir / "daily_order_limits.json", {
        "date": today.isoformat(),
        "buy_submit_count": 0,
        "sell_submit_count": 0,
        "last_updated": datetime.now().isoformat(),
    })

    # market context（macro_signals）— 給 _macro_buy_gate 用
    macro_label = (
        "macro_bullish" if macro_regime == "bullish"
        else "macro_cautious" if macro_regime == "cautious"
        else "macro_neutral"
    )
    _write_json(state_dir / "market_context_taiwan.json", {
        "market_regime": macro_regime,
        "risk_temperature": "normal",
        "core_tilt": "high",
        "income_tilt": "medium",
        "defensive_tilt": "low",
        "macro_signals": {
            "twii_vs_200ma_pct": 5.0,
            "vix": 18.0,
            "twii_60d_percentile": 65.0,
            "macro_score": 2,
            "macro_label": macro_label,
        },
        "strategy_ref": {"base_strategy": "平衡配置", "scenario_overlay": "無"},
    })

    # event context
    _write_json(state_dir / "market_event_context.json", {
        "event_regime": "neutral",
        "global_risk_level": "normal",
        "active_events": [],
        "summary": "",
    })

    # strategy
    _write_json(state_dir / "strategy_link.json", {
        "base_strategy": "平衡配置",
        "scenario_overlay": "無",
    })

    # phase 2 config
    _write_json(state_dir / "auto_trade_phase2_config.json", {"enabled": True})

    # cooldown / sensor / event
    _write_json(state_dir / "position_cooldown.json", {})
    _write_json(state_dir / "sensor_health.json", {"overall": "healthy"})
    _write_json(state_dir / "weekly_pnl.json", {"weekly_loss_triggered": False})
    _write_json(state_dir / "consecutive_loss_days.json", {"consecutive_buy_days": 0})

    # major events / risk
    _write_json(state_dir / "major_event_flag.json", {"level": "none", "active_until": None})
    _write_json(state_dir / "market_risk_state.json", {"risk_off": False})

    # DCA state（若有）
    if dca_state is not None:
        _write_json(state_dir / "initial_dca_state.json", dca_state)

    # Pre-existing pending queue：保留生產 buy_scanner 寫入的；不主動清空
    queue_path = state_dir / "pending_auto_orders.json"
    if not queue_path.exists():
        _write_json(queue_path, {"orders": []})

    # peak_tracker
    pt_path = state_dir / "position_peak_tracker.json"
    if not pt_path.exists():
        _write_json(pt_path, {"tracker": {}})


# ---------------------------------------------------------------------------
# Auto-ack：訊號出來直接吃下、扣現金/加股、不走 dashboard
# ---------------------------------------------------------------------------

def auto_ack_signal(signal: dict, *, cash: float, shares: int, avg_cost: float,
                    fill_price: float) -> tuple[float, int, float, dict]:
    """模擬訊號被 ack 後在帳本上的影響。回傳新的 cash/shares/avg_cost + trade record。"""
    qty = int(signal.get("quantity") or 0)
    side = signal.get("side", "").lower()
    if qty <= 0:
        return cash, shares, avg_cost, {}

    if side == "buy":
        cost = qty * fill_price
        fee = cost * BROKER_FEE_RATE
        total_out = cost + fee
        if cash < total_out:
            return cash, shares, avg_cost, {"skipped": "insufficient_cash"}
        new_shares = shares + qty
        new_avg = (avg_cost * shares + cost) / new_shares
        return cash - total_out, new_shares, new_avg, {
            "side": "buy", "qty": qty, "price": fill_price, "fee": fee,
            "trigger_source": signal.get("trigger_source"),
        }
    else:  # sell
        if qty > shares:
            qty = shares  # cap
        proceeds = qty * fill_price
        fee = proceeds * (BROKER_FEE_RATE + SELL_TAX_RATE)
        net = proceeds - fee
        new_shares = shares - qty
        new_avg = avg_cost if new_shares > 0 else 0.0
        return cash + net, new_shares, new_avg, {
            "side": "sell", "qty": qty, "price": fill_price, "fee": fee,
            "trigger_source": signal.get("trigger_source"),
        }


# ---------------------------------------------------------------------------
# Main replay loop
# ---------------------------------------------------------------------------

def run_replay(
    symbol: str,
    prices_df,
    *,
    initial_cash: float = 1_000_000.0,
    work_dir: Path,
    enable_dca: bool = True,
    dca_target_twd: float = 600_000,
    dca_target_days: int = 20,
) -> dict:
    """
    Args:
        symbol: e.g. '0050.TW'
        prices_df: pandas DataFrame from fetch_historical_prices, must have Close
        initial_cash: 起始資金
        work_dir: 用於 mock state 的目錄
        enable_dca: 是否啟用 DCA

    Returns:
        {
          'trades': [...],
          'equity_curve': [(date, equity), ...],
          'final_cash': float, 'final_shares': int, 'final_equity': float,
          'final_dca_state': dict,
        }
    """
    import os
    import pandas as pd

    # 設定 AGENT_ID 和 STATE 路徑指向 work_dir
    state_dir = work_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 注入 ctx：覆蓋 get_state_dir
    from scripts.etf_core import context as ctx_mod
    ctx_mod.get_state_dir = lambda: state_dir

    # 重要：buy_scanner 模組頂部已 `from etf_core import context as ctx_mod` 並用 `ctx_mod.get_state_dir()`
    # 但有些 import-time 變數會綁住舊值；force reimport 一次比較保險
    for mod_name in ['scripts.auto_trade.buy_scanner', 'scripts.auto_trade.sell_scanner',
                     'scripts.auto_trade.peak_tracker']:
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    from scripts.auto_trade.buy_scanner import run_buy_scan
    from scripts.auto_trade.sell_scanner import run_sell_scan
    from scripts.auto_trade import peak_tracker as pt
    from scripts.auto_trade.initial_dca import default_state, save_dca_state, load_dca_state

    bare_sym = symbol.replace(".TW", "").replace(".TWO", "")
    closes = prices_df["Close"].astype(float)

    # 初始化 DCA
    if enable_dca:
        dca = default_state()
        dca.update({
            "enabled": True,
            "total_target_twd": int(dca_target_twd),
            "target_days": int(dca_target_days),
            "started_on": str(closes.index[0].date()),
            "symbol_priority": [bare_sym],
        })
    else:
        dca = default_state()  # disabled

    # 初始化帳本
    cash = float(initial_cash)
    shares = 0
    avg_cost = 0.0
    trades: list[dict] = []
    equity_curve: list[tuple] = []

    # 初始化 peak_tracker（空）
    _write_json(state_dir / "position_peak_tracker.json", {"tracker": {}})

    prev_close: float | None = None

    for i, (idx, close) in enumerate(closes.items()):
        today = idx.date() if hasattr(idx, "date") else idx
        close_val = float(close)
        prev = float(prev_close) if prev_close is not None else close_val

        # 每天清空 pending queue（避免訊號跨日累積）
        _write_json(state_dir / "pending_auto_orders.json", {"orders": []})

        # 寫今日 state
        write_daily_state(
            state_dir,
            symbol=symbol,
            today=today,
            close=close_val,
            prev_close=prev,
            cash=cash,
            inventory_shares=shares,
            avg_cost=avg_cost,
            dca_state=dca,
        )

        # ── 09:30 買入掃描 ────────────────────────────────────────────────
        try:
            buy_res = run_buy_scan(
                trigger_time=time(9, 30),
                state_dir=state_dir,
                on_date=datetime.combine(today, time(9, 30), tzinfo=TW_TZ),
                skip_circuit_breaker=True,
            )
        except Exception as exc:
            buy_res = {"enqueued": [], "error": f"{type(exc).__name__}: {exc}"}

        # 自動 ack 所有 buy 訊號，按收盤價成交
        for sig in buy_res.get("enqueued", []):
            new_cash, new_shares, new_avg, trade = auto_ack_signal(
                sig, cash=cash, shares=shares, avg_cost=avg_cost,
                fill_price=close_val,
            )
            if trade and "skipped" not in trade:
                trade["date"] = str(today)
                trades.append(trade)
                cash, shares, avg_cost = new_cash, new_shares, new_avg
                # 若是 DCA 訊號 → 推進 DCA 狀態
                if sig.get("trigger_source") == "initial_dca":
                    payload = sig.get("trigger_payload", {})
                    dca["days_done"] = int(dca.get("days_done", 0)) + 1
                    dca["twd_spent"] = float(dca.get("twd_spent", 0)) + trade["qty"] * trade["price"]
                    dca["last_buy_date"] = str(today)
                    dca["next_symbol_idx"] = int(payload.get("next_symbol_idx", 0))
                    if dca["days_done"] >= int(dca["target_days"]):
                        dca["completed"] = True

        # ── peak_tracker 同步（每日更新）──────────────────────────────────
        if shares > 0:
            tracker = pt.load_tracker(state_dir)
            ret_pct = (close_val - avg_cost) / avg_cost if avg_cost > 0 else 0.0
            pt.upsert_position(
                tracker, symbol=bare_sym, entry_date=today - timedelta(days=2),
                group="core", today_close=close_val, today=today,
            )
            pt.update_close(tracker, symbol=bare_sym, close_price=close_val,
                            return_pct=ret_pct, on_date=today)
            pt.save_tracker(state_dir, tracker)

        # ── 13:15 賣出掃描 ───────────────────────────────────────────────
        if shares > 0:
            try:
                sell_res = run_sell_scan(
                    state_dir=state_dir,
                    on_date=datetime.combine(today, time(13, 15), tzinfo=TW_TZ),
                )
            except Exception as exc:
                sell_res = {"enqueued": [], "error": f"{type(exc).__name__}: {exc}"}


            for sig in sell_res.get("enqueued", []):
                new_cash, new_shares, new_avg, trade = auto_ack_signal(
                    sig, cash=cash, shares=shares, avg_cost=avg_cost,
                    fill_price=close_val,
                )
                if trade:
                    trade["date"] = str(today)
                    trades.append(trade)
                    cash, shares, avg_cost = new_cash, new_shares, new_avg
                    # 模擬 ack_handler.write_sell_cooldown 的副作用
                    from scripts.auto_trade.sell_scanner import write_sell_cooldown
                    write_sell_cooldown(state_dir, sig["symbol"],
                                        sold_on=datetime.combine(today, time(13, 15), tzinfo=TW_TZ))
                    # 賣完所有部位後清掉 peak_tracker entry（重新進場時重新追蹤）
                    if new_shares == 0:
                        tracker = pt.load_tracker(state_dir)
                        tracker.pop(bare_sym, None)
                        pt.save_tracker(state_dir, tracker)

        # 記錄當日資產
        equity = cash + shares * close_val
        equity_curve.append((str(today), equity))

        prev_close = close_val

    final_equity = cash + shares * float(closes.iloc[-1])
    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "final_cash": cash,
        "final_shares": shares,
        "final_equity": final_equity,
        "final_dca_state": dca,
        "initial_cash": initial_cash,
        "sell_dates": [t["date"] for t in trades if t["side"] == "sell"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    import tempfile

    from scripts.backtest.fetch_historical_prices import fetch_daily_history
    from scripts.backtest.strategy_simulator import (
        SimulationConfig,
        compute_metrics,
        simulate,
        simulate_buy_and_hold,
    )

    scenarios = [
        ("2024 Bull", "0050.TW", "2024-01-01", "2024-12-31"),
        ("2022 Bear", "0050.TW", "2022-01-01", "2022-12-31"),
        ("2020 COVID", "0050.TW", "2020-01-01", "2020-12-31"),
    ]

    print("=" * 78)
    print("Production Replay vs Simulator (B 計畫)")
    print("=" * 78)
    print()

    workspace = Path(tempfile.mkdtemp(prefix="etf_replay_"))
    print(f"Mock workspace: {workspace}")
    print()

    rows = []

    for name, sym, start, end in scenarios:
        print(f"--- {name} ({sym} {start} → {end}) ---")
        prices = fetch_daily_history(sym, start, end)
        if prices is None or len(prices) == 0:
            print(f"  (no data)")
            continue

        # Production replay
        rep_dir = workspace / name.replace(" ", "_").replace("(", "").replace(")", "")
        try:
            rep = run_replay(
                sym, prices, initial_cash=1_000_000,
                work_dir=rep_dir,
                enable_dca=True,
                dca_target_twd=600_000,
                dca_target_days=20,
            )
        except Exception as exc:
            print(f"  REPLAY ERROR: {type(exc).__name__}: {exc}")
            import traceback; traceback.print_exc()
            continue

        import pandas as pd
        rep_curve = pd.Series(
            [v for _, v in rep["equity_curve"]],
            index=[d for d, _ in rep["equity_curve"]],
        )
        rep_metrics = compute_metrics(rep_curve)
        rep_buys = sum(1 for t in rep["trades"] if t["side"] == "buy")
        rep_sells = sum(1 for t in rep["trades"] if t["side"] == "sell")
        rep_dca_buys = sum(1 for t in rep["trades"] if t.get("trigger_source") == "initial_dca")

        # Simulator
        cfg = SimulationConfig(
            initial_cash=1_000_000, symbol_group="core",
            max_position_pct=0.95, initial_dca_target_pct=0.6, initial_dca_days=20,
        )
        sim = simulate(prices, cfg)
        sim_metrics = compute_metrics(sim.equity_curve)
        sim_buys = sum(1 for t in sim.trades if t.side == "buy")
        sim_sells = sum(1 for t in sim.trades if t.side == "sell")
        sim_dca_buys = sum(1 for t in sim.trades if "initial_dca" in (t.note or ""))

        # BAH
        bah = simulate_buy_and_hold(prices, initial_cash=1_000_000)
        bah_metrics = compute_metrics(bah.equity_curve)

        gap = (rep_metrics["total_return_pct"] or 0) - (sim_metrics["total_return_pct"] or 0)
        rows.append({
            "name": name,
            "rep_return": rep_metrics["total_return_pct"],
            "sim_return": sim_metrics["total_return_pct"],
            "bah_return": bah_metrics["total_return_pct"],
            "gap": gap,
            "rep_dd": rep_metrics["max_drawdown_pct"],
            "sim_dd": sim_metrics["max_drawdown_pct"],
            "rep_buys": rep_buys, "sim_buys": sim_buys,
            "rep_sells": rep_sells, "sim_sells": sim_sells,
            "rep_dca": rep_dca_buys, "sim_dca": sim_dca_buys,
        })

        print(f"  Production : {rep_metrics['total_return_pct']:+7.2f}%  DD {rep_metrics['max_drawdown_pct']:6.2f}%  ({rep_buys:3d}buy/{rep_sells:2d}sell, DCA {rep_dca_buys})")
        if rep["sell_dates"]:
            uniq = sorted(set(rep["sell_dates"]))
            print(f"  rep sell dates: {uniq[:5]}{'...' if len(uniq)>5 else ''}")
        sim_sell_dates = sorted(set(t.date for t in sim.trades if t.side == 'sell'))
        if sim_sell_dates:
            print(f"  sim sell dates: {sim_sell_dates}")
        print(f"  Simulator  : {sim_metrics['total_return_pct']:+7.2f}%  DD {sim_metrics['max_drawdown_pct']:6.2f}%  ({sim_buys:3d}buy/{sim_sells:2d}sell, DCA {sim_dca_buys})")
        print(f"  BAH        : {bah_metrics['total_return_pct']:+7.2f}%  DD {bah_metrics['max_drawdown_pct']:6.2f}%")
        print(f"  Gap (Rep - Sim) = {gap:+.2f}%")
        print()

    # Summary
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"{'Scenario':<18} {'Production':>12} {'Simulator':>12} {'BAH':>10} {'Gap':>10}")
    for r in rows:
        print(f"{r['name']:<18} {r['rep_return']:+11.2f}% {r['sim_return']:+11.2f}% {r['bah_return']:+9.2f}% {r['gap']:+9.2f}%")
    print()

    out_dir = ROOT / "docs/intelligence-roadmap/backtest-reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    today_iso = date.today().isoformat()
    out_path = out_dir / f"{today_iso}-production-replay.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
