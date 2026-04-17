"""
backtest_decision_outcomes.py — AI 決策歷史回測引擎

讀取 ai_decision_outcome.jsonl，計算各交易的 PnL、勝率、最大回撤、夏普比率，
並判定品質閘門（win_rate >= 0.5 AND max_drawdown <= 0.15）。

輸出 backtest_results.json 供 10-05 live mode 解鎖閘門讀取。
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

# --- 路徑注入（讓 scripts 模組可被匯入）---
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from etf_core.context import get_state_dir
from etf_core.state_io import safe_load_jsonl, atomic_save_json

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------

def compute_trade_pnl(entry_price: float, exit_price: float, action: str) -> float:
    """計算單筆交易損益率。

    buy / preview_buy  : (exit - entry) / entry
    sell / preview_sell: (entry - exit) / entry  （價格下跌獲利）
    """
    action_lower = action.lower()
    if action_lower in ("buy", "preview_buy"):
        return (exit_price - entry_price) / entry_price
    else:
        return (entry_price - exit_price) / entry_price


def compute_metrics(pnl_list: list[float]) -> dict:
    """從 PnL 列表計算績效指標。"""
    if not pnl_list:
        return {
            "win_rate": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
            "avg_pnl": None,
        }

    n = len(pnl_list)
    win_rate = sum(1 for p in pnl_list if p > 0) / n

    # --- 最大回撤（equity curve） ---
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for p in pnl_list:
        equity += p
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    avg_pnl = sum(pnl_list) / n

    # --- 夏普比率（年化） ---
    sharpe = None
    if n >= 2:
        if _HAS_NUMPY:
            arr = np.array(pnl_list, dtype=float)
            std = float(np.std(arr, ddof=1))
            mean = float(np.mean(arr))
        else:
            mean = avg_pnl
            variance = sum((p - mean) ** 2 for p in pnl_list) / (n - 1)
            std = math.sqrt(variance)
            mean = avg_pnl

        sharpe = (mean / std * math.sqrt(252)) if std > 1e-12 else None

    return {
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "avg_pnl": avg_pnl,
    }


def evaluate_quality_gate(
    win_rate: Optional[float],
    max_drawdown: Optional[float],
) -> bool:
    """品質閘門：win_rate >= 0.5 AND max_drawdown <= 0.15。"""
    if win_rate is None or max_drawdown is None:
        return False
    return win_rate >= 0.5 and max_drawdown <= 0.15


# ---------------------------------------------------------------------------
# Price fetcher (production — uses yfinance)
# ---------------------------------------------------------------------------

def fetch_price(
    symbol: str,
    date_str: str,
    price_cache: dict,
) -> Optional[float]:
    """從 yfinance 取得指定日期的收盤價。失敗時回傳 None。"""
    cache_key = (symbol, date_str)
    if cache_key in price_cache:
        return price_cache[cache_key]

    try:
        import yfinance as yf

        # Taiwan ETF ticker convention
        if symbol.startswith("006"):
            ticker = symbol + ".TWO"
        else:
            ticker = symbol + ".TW"

        # yfinance end date is exclusive — add 7 days to catch trading days
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = dt + timedelta(days=7)
        end_str = end_dt.strftime("%Y-%m-%d")

        df = yf.download(ticker, start=date_str, end=end_str, auto_adjust=True, progress=False)
        if df.empty:
            price_cache[cache_key] = None
            return None

        # 取最近一個可用交易日的收盤價
        # yfinance 新版本 Close 可能是 multi-index DataFrame，需 squeeze
        close_col = "Close"
        if close_col not in df.columns:
            price_cache[cache_key] = None
            return None

        close_data = df[close_col]
        # multi-index: squeeze to Series, then take first scalar
        if hasattr(close_data, "squeeze"):
            close_data = close_data.squeeze()
        # 取第一個有效值
        first_val = close_data.iloc[0]
        # 若仍為 Series（multi-ticker 情況），再取第一個
        try:
            price = float(first_val)
        except (TypeError, ValueError):
            first_val2 = first_val.iloc[0] if hasattr(first_val, "iloc") else first_val
            price = float(first_val2)
        price_cache[cache_key] = price
        return price

    except Exception as e:
        print(f"[backtest] WARNING: 無法取得 {symbol} 於 {date_str} 的價格：{e}")
        price_cache[cache_key] = None
        return None


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------

_TRADEABLE_ACTIONS = {"preview_buy", "preview_sell", "buy", "sell"}


def run_backtest(
    records: list[dict],
    holding_days: int = 5,
    price_fetcher: Optional[Callable[[str, str], Optional[float]]] = None,
) -> dict:
    """執行回測。

    price_fetcher: (symbol, date_str) -> float | None
        - 測試時注入 mock；正式執行時使用 fetch_price 包裝。
    """
    price_cache: dict = {}

    def _get_price(symbol: str, date_str: str) -> Optional[float]:
        if price_fetcher is not None:
            return price_fetcher(symbol, date_str)
        return fetch_price(symbol, date_str, price_cache)

    total = len(records)
    tradeable = [r for r in records if r.get("action", "").lower() in _TRADEABLE_ACTIONS]
    trades = []

    for rec in tradeable:
        symbol = rec.get("symbol", "")
        action = rec.get("action", "")
        recorded_at_str = rec.get("recorded_at", "")

        # 解析日期
        try:
            if "T" in recorded_at_str:
                entry_dt = datetime.fromisoformat(recorded_at_str).date()
            else:
                entry_dt = datetime.strptime(recorded_at_str, "%Y-%m-%d").date()
        except Exception:
            continue

        entry_date_str = entry_dt.strftime("%Y-%m-%d")
        exit_dt = entry_dt + timedelta(days=holding_days)
        exit_date_str = exit_dt.strftime("%Y-%m-%d")

        entry_price = _get_price(symbol, entry_date_str)
        exit_price = _get_price(symbol, exit_date_str)

        if entry_price is None or exit_price is None:
            continue

        pnl = compute_trade_pnl(entry_price, exit_price, action)
        trades.append({
            "symbol": symbol,
            "action": action,
            "entry_date": entry_date_str,
            "exit_date": exit_date_str,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
        })

    pnl_list = [t["pnl"] for t in trades]
    metrics = compute_metrics(pnl_list)

    gate_passed = evaluate_quality_gate(metrics["win_rate"], metrics["max_drawdown"])

    if not trades:
        gate_reason = "insufficient data"
    elif not gate_passed:
        reasons = []
        if metrics["win_rate"] is not None and metrics["win_rate"] < 0.5:
            reasons.append(f"win_rate={metrics['win_rate']:.2f} < 0.50")
        if metrics["max_drawdown"] is not None and metrics["max_drawdown"] > 0.15:
            reasons.append(f"max_drawdown={metrics['max_drawdown']:.2f} > 0.15")
        gate_reason = "; ".join(reasons) if reasons else "threshold not met"
    else:
        gate_reason = "passed"

    return {
        "total_decisions_evaluated": total,
        "tradeable_decisions": len(tradeable),
        "trades_with_price_data": len(trades),
        "trade_details": trades,
        "win_rate": metrics["win_rate"],
        "max_drawdown": metrics["max_drawdown"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "avg_pnl": metrics["avg_pnl"],
        "avg_holding_days": holding_days,
        "quality_gate_passed": gate_passed,
        "quality_gate_reason": gate_reason,
        "last_updated": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AI 決策歷史回測引擎")
    parser.add_argument("--holding-days", type=int, default=5, help="持倉天數（日曆天）")
    args = parser.parse_args()

    state_dir = get_state_dir()
    outcome_path = state_dir / "ai_decision_outcome.jsonl"
    output_path = state_dir / "backtest_results.json"

    records = safe_load_jsonl(outcome_path) if outcome_path.exists() else []
    print(f"[backtest] 載入 {len(records)} 筆決策紀錄 from {outcome_path}")

    result = run_backtest(records, holding_days=args.holding_days)

    atomic_save_json(output_path, result)
    print(
        f"[backtest] {result['trades_with_price_data']} trades evaluated. "
        f"win_rate={result['win_rate'] or 0:.2f}, "
        f"max_drawdown={result['max_drawdown'] or 0:.2f}, "
        f"gate_passed={result['quality_gate_passed']}"
    )
    print(f"[backtest] 結果已寫入 {output_path}")


if __name__ == "__main__":
    main()
