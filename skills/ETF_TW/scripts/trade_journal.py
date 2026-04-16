#!/usr/bin/env python3
"""
ETF_TW Trade Journal — EOD 歸檔與復盤系統

功能：
1. 串接 decision_id ↔ order_id，打通決策→委託→成交的完整軌跡
2. 計算 slippage（建議限價 vs 實際成交價）
3. 產出每日歸檔 JSON（含完整軌跡、未成交原因、slippage 分析）
4. 支援復盤查詢

資料來源：
- decision_log.jsonl — 決策快照（誰決定、建議、信心）
- auto_preview_candidate.json — 共識仲裁結果
- orders_open.json — 委託落地（broker_order_id、限價、狀態）
- trade_logs.jsonl — 成交紀錄（實際成交價、費用）
- positions.json — 最終持倉（交叉驗證用）

歸檔輸出：
- state/trade_journal/{date}.json — 當日完整軌跡歸檔
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

# --- Path setup ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys_path_appended = False
if str(ROOT) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(ROOT))
    sys_path_appended = True

try:
    from scripts.etf_core import context
    STATE_DIR = context.get_state_dir()
except Exception:
    STATE_DIR = ROOT / "instances" / "etf_master" / "state"

TRADE_LOGS_PATH = ROOT / "data" / "trade_logs.jsonl"
JOURNAL_DIR = STATE_DIR / "trade_journal"


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


# ---------------------------------------------------------------------------
# Core: Build a day's trade journal
# ---------------------------------------------------------------------------

def build_daily_journal(target_date: str | None = None) -> dict:
    """
    Build a complete trade journal for a given date.

    target_date: ISO date string (YYYY-MM-DD). Defaults to today.
    Returns: dict with full decision→order→fill trace + slippage analysis.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    # 1. Load all data sources
    decision_log = _load_jsonl(STATE_DIR / "decision_log.jsonl")
    preview_candidate = _load_json(STATE_DIR / "auto_preview_candidate.json")
    orders_open = _load_json(STATE_DIR / "orders_open.json")
    trade_logs = _load_jsonl(TRADE_LOGS_PATH)
    positions = _load_json(STATE_DIR / "positions.json")
    consensus = preview_candidate.get("consensus", {})

    # 2. Filter decisions for target date
    date_decisions = []
    for entry in decision_log:
        ts = entry.get("scanned_at", "")
        if ts.startswith(target_date):
            date_decisions.append(entry)

    # 3. Filter trade_logs for target date
    date_trades = []
    for entry in trade_logs:
        ts = entry.get("timestamp", "")
        if ts.startswith(target_date):
            date_trades.append(entry)

    # 4. Filter orders_open for target date
    date_orders = []
    for order in orders_open.get("orders", []):
        ts = order.get("submitted_at", "")
        if ts.startswith(target_date):
            date_orders.append(order)

    # 5. Build traces: decision → order → fill
    traces = []
    for decision in date_decisions:
        decision_id = decision.get("decision_id", "")
        symbol = None
        suggested_price = None
        action = decision.get("action", "")

        # Extract symbol and suggested price from top_candidates
        top_candidates = decision.get("top_candidates", [])
        if top_candidates:
            top = top_candidates[0]
            symbol = top.get("symbol")
            suggested_price = top.get("price")

        # Also check preview candidate for today's consensus
        matched_consensus = {}
        if symbol and consensus.get("rule_engine_symbol") == symbol:
            matched_consensus = consensus

        # Find matching order
        matched_order = None
        matched_fill = None
        for order in date_orders:
            if order.get("symbol") == symbol:
                matched_order = order
                # Check fill
                if order.get("status") == "filled":
                    for trade in date_trades:
                        if (trade.get("symbol") == symbol and
                            trade.get("action") == "order_filled"):
                            matched_fill = trade
                break

        # If no order matched by orders_open, try trade_logs
        if not matched_order:
            for trade in date_trades:
                if (trade.get("symbol") == symbol and
                    trade.get("action") in ("order_submitted", "order_filled")):
                    matched_order = trade
                    break

        # Calculate slippage
        filled_price = None
        slippage = None
        slippage_pct = None
        if matched_order and matched_order.get("filled_price"):
            filled_price = float(matched_order["filled_price"])
        elif matched_fill and matched_fill.get("price"):
            filled_price = float(matched_fill["price"])

        if filled_price and suggested_price and suggested_price > 0:
            slippage = filled_price - suggested_price
            slippage_pct = (slippage / suggested_price) * 100

        # Build trace entry
        trace = {
            "decision_id": decision_id,
            "decision_time": decision.get("scanned_at"),
            "action": action,
            "symbol": symbol,
            "suggested_price": suggested_price,
            "consensus": matched_consensus if matched_consensus else None,
            "order": _extract_order_summary(matched_order) if matched_order else None,
            "fill": _extract_fill_summary(matched_fill) if matched_fill else (
                _extract_fill_summary(matched_order) if matched_order and matched_order.get("filled_price") else None
            ),
            "slippage": _round_safe(slippage),
            "slippage_pct": _round_safe(slippage_pct),
            "outcome": _determine_outcome(action, matched_order, matched_fill),
        }
        traces.append(trace)

    # 6. Also check: orders that exist but have no matching decision (manual trades)
    traced_symbols = {t.get("symbol") for t in traces if t.get("symbol")}
    for order in date_orders:
        if order.get("symbol") not in traced_symbols:
            trace = {
                "decision_id": None,
                "decision_time": None,
                "action": "manual",
                "symbol": order.get("symbol"),
                "suggested_price": None,
                "consensus": None,
                "order": _extract_order_summary(order),
                "fill": _extract_fill_summary(order) if order.get("filled_price") else None,
                "slippage": None,
                "slippage_pct": None,
                "outcome": "filled-manual" if order.get("status") == "filled" else "pending-manual",
            }
            traces.append(trace)

    # 7. Summary statistics
    total_decisions = len(date_decisions)
    total_orders = len(date_orders)
    total_filled = sum(1 for t in traces if "filled" in (t.get("outcome") or ""))
    total_unfilled = sum(1 for t in traces if "unfilled" in (t.get("outcome") or ""))
    total_manual = sum(1 for t in traces if t.get("action") == "manual")
    slippages = [t["slippage"] for t in traces if t.get("slippage") is not None]

    avg_slippage = sum(slippages) / len(slippages) if slippages else None
    max_slippage = max(slippages) if slippages else None

    journal = {
        "date": target_date,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": "trade_journal",
        "strategy_snapshot": {
            "base_strategy": preview_candidate.get("strategy", {}).get("base_strategy"),
            "scenario_overlay": preview_candidate.get("strategy", {}).get("scenario_overlay"),
        },
        "summary": {
            "total_decisions": total_decisions,
            "total_orders_sent": total_orders,
            "total_filled": total_filled,
            "total_unfilled": total_unfilled,
            "total_manual_trades": total_manual,
            "fill_rate": _round_safe(total_filled / total_orders) if total_orders > 0 else None,
            "avg_slippage": _round_safe(avg_slippage),
            "max_slippage": _round_safe(max_slippage),
        },
        "traces": traces,
        "positions_eod": _extract_positions_summary(positions),
    }
    return journal


def _extract_order_summary(order: dict | None) -> dict | None:
    if not order:
        return None
    return {
        "order_id": order.get("order_id") or order.get("broker_order_id"),
        "broker_order_id": order.get("broker_order_id"),
        "symbol": order.get("symbol"),
        "action": order.get("action") or order.get("order_action"),
        "quantity": order.get("quantity"),
        "price": order.get("price"),
        "status": order.get("status"),
        "submitted_at": order.get("submitted_at") or order.get("timestamp"),
        "verified": order.get("verified"),
    }


def _extract_fill_summary(fill: dict | None) -> dict | None:
    if not fill:
        return None
    return {
        "filled_price": fill.get("filled_price") or fill.get("price"),
        "filled_quantity": fill.get("filled_quantity") or fill.get("quantity"),
        "fee": fill.get("fee"),
        "tax": fill.get("tax"),
        "filled_at": fill.get("timestamp"),
    }


def _determine_outcome(action: str, order: dict | None, fill: dict | None) -> str:
    if not order:
        return "decision-only-no-order"

    status = order.get("status", "")
    if status == "filled":
        return "filled"
    elif status in ("cancelled", "rejected"):
        reason = order.get("error") or "unknown"
        return f"unfilled:{status}:{reason}"
    elif status in ("submitted", "partial_filled"):
        return "pending"
    else:
        return f"unknown:{status}"


def _round_safe(val: float | None) -> float | None:
    if val is None:
        return None
    return round(float(val), 4)


def _extract_positions_summary(positions: dict) -> dict:
    """Extract a simplified positions summary for EOD snapshot."""
    # Support both "positions" and "holdings" keys
    holdings = positions.get("positions") or positions.get("holdings") or []
    summary = []
    for h in holdings:
        summary.append({
            "symbol": h.get("symbol"),
            "quantity": h.get("quantity"),
            "avg_cost": h.get("average_price") or h.get("avg_cost") or h.get("cost_basis"),
            "market_value": h.get("market_value"),
            "unrealized_pnl": h.get("unrealized_pnl"),
        })
    cash = positions.get("cash") or positions.get("cash_available")
    total_equity = positions.get("total_equity") or positions.get("total_value")
    if not total_equity and summary:
        total_equity = sum(h.get("market_value", 0) or 0 for h in holdings) + (cash or 0)
    return {
        "holdings": summary,
        "cash": cash,
        "total_equity": total_equity,
    }


# ---------------------------------------------------------------------------
# IO: Save / Load journal
# ---------------------------------------------------------------------------

def save_journal(journal: dict) -> Path:
    """Save journal to state/trade_journal/{date}.json"""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    target_date = journal.get("date", date.today().isoformat())
    path = JOURNAL_DIR / f"{target_date}.json"
    path.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_journal(target_date: str) -> dict | None:
    """Load a specific date's journal."""
    path = JOURNAL_DIR / f"{target_date}.json"
    if not path.exists():
        return None
    return _load_json(path)


def list_journals() -> list[str]:
    """List all available journal dates."""
    if not JOURNAL_DIR.exists():
        return []
    return sorted(
        p.stem for p in JOURNAL_DIR.glob("*.json")
        if p.stem.count("-") == 2  # YYYY-MM-DD format
    )


# ---------------------------------------------------------------------------
# Backfill: Build journal from existing historical data
# ---------------------------------------------------------------------------

def backfill_journals() -> list[str]:
    """
    Scan decision_log.jsonl for all dates that have decisions,
    build journals for each date that doesn't already have one.
    """
    decision_log = _load_jsonl(STATE_DIR / "decision_log.jsonl")
    trade_logs = _load_jsonl(TRADE_LOGS_PATH)

    # Collect all dates
    all_dates = set()
    for entry in decision_log:
        ts = entry.get("scanned_at", "")
        if ts:
            all_dates.add(ts[:10])
    for entry in trade_logs:
        ts = entry.get("timestamp", "")
        if ts:
            all_dates.add(ts[:10])

    existing = set(list_journals())
    new_journals = []
    for d in sorted(all_dates):
        if d not in existing:
            journal = build_daily_journal(d)
            save_journal(journal)
            new_journals.append(d)

    return new_journals


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ETF_TW Trade Journal — EOD 歸檔與復盤")
    parser.add_argument("--date", default=None, help="Target date (YYYY-MM-DD), default=today")
    parser.add_argument("--backfill", action="store_true", help="Backfill journals for all historical dates")
    parser.add_argument("--list", action="store_true", help="List available journals")
    parser.add_argument("--show", default=None, help="Show a specific date's journal")
    args = parser.parse_args()

    if args.list:
        journals = list_journals()
        if journals:
            print("Available journals:")
            for j in journals:
                print(f"  {j}")
        else:
            print("No journals found. Run --backfill or --date to create one.")
    elif args.backfill:
        new = backfill_journals()
        if new:
            print(f"Backfilled {len(new)} journals: {', '.join(new)}")
        else:
            print("All dates already have journals.")
    elif args.show:
        journal = load_journal(args.show)
        if journal:
            print(json.dumps(journal, ensure_ascii=False, indent=2))
        else:
            print(f"No journal found for {args.show}")
    else:
        journal = build_daily_journal(args.date)
        path = save_journal(journal)
        print(f"Journal saved: {path}")
        # Print summary
        s = journal.get("summary", {})
        print(f"\n--- {journal['date']} 歸檔摘要 ---")
        print(f"  決策數: {s.get('total_decisions', 0)}")
        print(f"  送單數: {s.get('total_orders_sent', 0)}")
        print(f"  成交數: {s.get('total_filled', 0)}")
        print(f"  未成交: {s.get('total_unfilled', 0)}")
        print(f"  手動單: {s.get('total_manual_trades', 0)}")
        print(f"  成交率: {s.get('fill_rate', 'N/A')}")
        print(f"  平均滑價: {s.get('avg_slippage', 'N/A')}")
        print(f"  最大滑價: {s.get('max_slippage', 'N/A')}")
        # Print traces
        for t in journal.get("traces", []):
            symbol = t.get("symbol", "?")
            action = t.get("action", "?")
            outcome = t.get("outcome", "?")
            slip = t.get("slippage")
            slip_str = f" (滑價: {slip})" if slip is not None else ""
            print(f"  [{symbol}] {action} → {outcome}{slip_str}")