"""
Unit tests for run_paper_stress_test.py
Ghost order detection and unit confusion logic.
All tests use inline fixture dicts — no real state files read.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_paper_stress_test import check_cycle_orders, run_stress_test


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _clean_board(order_id="o1"):
    return {
        "order_id": order_id,
        "symbol": "0050",
        "side": "buy",
        "quantity": 1000,
        "lot_type": "board",
        "broker_order_id": "B123",
        "verified": True,
        "tier": 1,
        "mode": "paper",
    }


# ── check_cycle_orders tests ──────────────────────────────────────────────────

def test_ghost_order_detected_on_null_broker_id():
    """broker_order_id=None + verified=False → ghost_orders list non-empty."""
    orders = [
        {**_clean_board(), "broker_order_id": None, "verified": False},
    ]
    result = check_cycle_orders(orders)
    assert len(result["ghost_orders"]) == 1
    assert result["ghost_orders"][0]["order_id"] == "o1"


def test_ghost_order_detected_on_empty_string_broker_id():
    """broker_order_id="" + verified=False → ghost_orders list non-empty."""
    orders = [
        {**_clean_board(), "broker_order_id": "", "verified": False},
    ]
    result = check_cycle_orders(orders)
    assert len(result["ghost_orders"]) == 1


def test_unit_confusion_detected_for_non_1000_board_lot():
    """Board lot with quantity=500 (not multiple of 1000) → unit_confusion detected."""
    orders = [
        {**_clean_board(), "quantity": 500, "lot_type": "board"},
    ]
    result = check_cycle_orders(orders)
    assert len(result["unit_confusion"]) == 1


def test_clean_board_lot_1000_shares_no_confusion():
    """Board lot quantity=1000 → no unit_confusion."""
    orders = [_clean_board()]
    result = check_cycle_orders(orders)
    assert result["unit_confusion"] == []
    assert result["ghost_orders"] == []


def test_odd_lot_nonmultiple_no_confusion():
    """Odd lot with quantity=500 → NOT unit_confusion (odd lots are legitimately non-multiples)."""
    orders = [
        {**_clean_board(), "quantity": 500, "lot_type": "odd"},
    ]
    result = check_cycle_orders(orders)
    assert result["unit_confusion"] == []


# ── run_stress_test tests ─────────────────────────────────────────────────────

def test_duplicate_order_ids_detected():
    """Two cycles returning same order_id → duplicate_order_ids non-empty."""
    orders = [_clean_board(order_id="dup-01")]  # same order_id every cycle
    report = run_stress_test(cycles=2, scan_fn=lambda: orders)
    assert "dup-01" in report["duplicate_order_ids"]


def test_all_clean_cycles_pass():
    """10 clean cycles → stress_test_passed=True, no ghost, no confusion."""
    clean_orders = [
        {"order_id": f"o{i}", "lot_type": "board", "quantity": 1000,
         "broker_order_id": "B123", "verified": True, "tier": 1}
        for i in range(3)
    ]
    report = run_stress_test(cycles=10, scan_fn=lambda: clean_orders)
    assert report["stress_test_passed"] is True
    assert report["ghost_orders_detected"] == 0
    assert report["unit_confusion_detected"] == 0


def test_any_ghost_causes_failure():
    """A single ghost order in any cycle → stress_test_passed=False."""
    ghost_orders = [
        {**_clean_board(), "broker_order_id": None, "verified": False},
    ]
    report = run_stress_test(cycles=3, scan_fn=lambda: ghost_orders)
    assert report["stress_test_passed"] is False
    assert report["ghost_orders_detected"] > 0


def test_tier_distribution_counts():
    """tier_distribution sums to total_orders_seen across all cycles."""
    orders = [
        {**_clean_board(order_id=f"t1-{i}"), "tier": 1} for i in range(2)
    ] + [
        {**_clean_board(order_id=f"t2-{i}"), "tier": 2} for i in range(1)
    ]
    report = run_stress_test(cycles=4, scan_fn=lambda: orders)
    dist = report["tier_distribution"]
    assert dist["tier1"] + dist["tier2"] + dist["tier3"] == report["total_orders_seen"]
