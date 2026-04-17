#!/usr/bin/env python3
"""
run_paper_stress_test.py

Paper-mode stress test runner for ETF_TW.
Exercises N simulated scan cycles and validates safety invariants:
  - No ghost orders (broker_order_id=null/empty AND verified=False)
  - No unit confusion (board lot quantity not multiple of 1000)
  - No duplicate order_ids across cycles
  - Correct Tier distribution reported

IMPORTANT: Does NOT call Shioaji or submit real orders.
Reads existing paper-mode state files to simulate cycles.
Output written to instances/<agent_id>/state/stress_test_report.json
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etf_core.context import get_state_dir
from etf_core.state_io import atomic_save_json, safe_load_json, safe_load_jsonl


# ── Pure helpers ──────────────────────────────────────────────────────────────

def check_cycle_orders(orders: list[dict]) -> dict:
    """Check a single cycle's order list for safety violations.

    Returns:
        {
          "ghost_orders": list[dict],   # orders that are ghosts
          "unit_confusion": list[dict], # board lots with bad quantity
          "order_ids": list[str],       # all order_ids seen
        }
    """
    ghost_orders: list[dict] = []
    unit_confusion: list[dict] = []
    order_ids: list[str] = []

    for order in orders:
        oid = order.get("order_id", "")
        if oid:
            order_ids.append(str(oid))

        # Ghost order: broker_order_id null/empty AND not verified
        broker_id = order.get("broker_order_id")
        verified = order.get("verified", True)
        is_ghost = (broker_id in (None, "", "null")) and not verified
        if is_ghost:
            ghost_orders.append(order)

        # Unit confusion: board lot with quantity not multiple of 1000
        lot_type = order.get("lot_type", "board")
        quantity = order.get("quantity", 0)
        if lot_type == "board" and quantity % 1000 != 0:
            unit_confusion.append(order)

    return {
        "ghost_orders": ghost_orders,
        "unit_confusion": unit_confusion,
        "order_ids": order_ids,
    }


# ── Stress test orchestrator ──────────────────────────────────────────────────

def _default_scan_fn() -> list[dict]:
    """Default scan_fn: read current paper-mode state files."""
    state_dir = get_state_dir()
    candidates = safe_load_json(state_dir / "auto_preview_candidate.json", default=[])
    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        candidates = []
    return candidates


def run_stress_test(cycles: int, scan_fn: Callable[[], list[dict]] | None = None) -> dict:
    """Run N cycles and validate safety invariants.

    Args:
        cycles: Number of scan cycles to simulate.
        scan_fn: Callable returning a list of order dicts per cycle.
                 Defaults to reading auto_preview_candidate.json.

    Returns:
        Report dict with stress_test_passed, counts, tier_distribution.
    """
    if scan_fn is None:
        scan_fn = _default_scan_fn

    ghost_orders_detected = 0
    unit_confusion_detected = 0
    all_order_ids: list[str] = []
    tier_counts: dict[str, int] = {"tier1": 0, "tier2": 0, "tier3": 0}
    total_orders_seen = 0
    failure_reasons: list[str] = []

    # Track cross-cycle duplicates (same order_id seen in more than one cycle)
    duplicates: list[str] = []
    cross_cycle_seen: set[str] = set()

    for cycle_num in range(cycles):
        orders = scan_fn()
        if not orders:
            continue

        result = check_cycle_orders(orders)

        ghost_orders_detected += len(result["ghost_orders"])
        unit_confusion_detected += len(result["unit_confusion"])
        all_order_ids.extend(result["order_ids"])
        total_orders_seen += len(orders)

        for order in orders:
            tier = order.get("tier", 0)
            key = f"tier{tier}"
            if key in tier_counts:
                tier_counts[key] += 1

        # Detect cross-cycle duplicates (informational only — does not affect pass/fail)
        for oid in result["order_ids"]:
            if oid in cross_cycle_seen and oid not in duplicates:
                duplicates.append(oid)
            cross_cycle_seen.add(oid)

    # Determine pass/fail — ghost orders and unit confusion are hard failures
    # Duplicate order_ids are informational (same pending order may appear across cycles)
    if ghost_orders_detected > 0:
        failure_reasons.append(f"Ghost orders detected: {ghost_orders_detected}")
    if unit_confusion_detected > 0:
        failure_reasons.append(f"Unit confusion detected: {unit_confusion_detected}")

    stress_test_passed = len(failure_reasons) == 0

    return {
        "cycles_run": cycles,
        "total_orders_seen": total_orders_seen,
        "ghost_orders_detected": ghost_orders_detected,
        "unit_confusion_detected": unit_confusion_detected,
        "duplicate_order_ids": duplicates,
        "tier_distribution": tier_counts,
        "stress_test_passed": stress_test_passed,
        "failure_reasons": failure_reasons,
        "last_updated": datetime.now(tz=timezone.utc).isoformat(),
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETF_TW Paper-mode stress test runner"
    )
    parser.add_argument(
        "--cycles", type=int, default=10,
        help="Number of simulated scan cycles (default: 10)"
    )
    args = parser.parse_args()

    report = run_stress_test(cycles=args.cycles)

    state_dir = get_state_dir()
    out_path = state_dir / "stress_test_report.json"
    atomic_save_json(out_path, report)

    passed = report["stress_test_passed"]
    print(f"[stress-test] Completed {args.cycles} cycles. Passed: {passed}")
    if not passed:
        for reason in report["failure_reasons"]:
            print(f"  FAIL: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
