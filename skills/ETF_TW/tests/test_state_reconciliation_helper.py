from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/state_reconciliation.py")
spec = importlib.util.spec_from_file_location("state_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_reconciliation_summary_detects_clean_alignment_and_open_order_gap():
    positions = {
        "positions": [
            {"symbol": "0050"},
            {"symbol": "00878"},
        ],
        "updated_at": "2026-04-02T23:26:04.421413",
    }
    snapshot = {
        "holdings": [
            {"symbol": "0050"},
            {"symbol": "00878"},
        ],
        "updated_at": "2026-04-02T23:26:06.463879",
    }
    orders_open = {
        "orders": [
            {"symbol": "00922", "status": "submitted"}
        ]
    }
    summary = module.reconciliation_summary(positions, snapshot, orders_open)
    assert summary["positions_vs_snapshot_match"] is True
    assert summary["open_orders_not_in_positions"] == ["00922"]
    assert summary["open_orders_not_in_snapshot"] == ["00922"]
    assert summary["snapshot_lag_sec"] is not None


def test_reconciliation_summary_detects_positions_snapshot_drift():
    positions = {
        "positions": [{"symbol": "0050"}],
        "updated_at": "2026-04-02T23:26:04.421413",
    }
    snapshot = {
        "holdings": [{"symbol": "00878"}],
        "updated_at": "2026-04-02T23:26:06.463879",
    }
    orders_open = {"orders": []}
    summary = module.reconciliation_summary(positions, snapshot, orders_open)
    assert summary["positions_vs_snapshot_match"] is False
    assert summary["position_symbols"] == ["0050"]
    assert summary["holding_symbols"] == ["00878"]
