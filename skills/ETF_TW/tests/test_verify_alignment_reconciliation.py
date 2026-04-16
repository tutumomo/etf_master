from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/state_reconciliation.py")
spec = importlib.util.spec_from_file_location("state_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_reconciliation_summary_shape_for_alignment_diagnostic():
    positions = {
        "positions": [{"symbol": "0050"}],
        "updated_at": "2026-04-02T23:26:04.421413",
    }
    snapshot = {
        "holdings": [{"symbol": "0050"}],
        "updated_at": "2026-04-02T23:26:06.463879",
    }
    orders_open = {
        "orders": [{"symbol": "00922", "status": "submitted"}]
    }
    recon = module.reconciliation_summary(positions, snapshot, orders_open)
    assert "positions_vs_snapshot_match" in recon
    assert "open_orders_not_in_positions" in recon
    assert recon["open_orders_not_in_positions"] == ["00922"]
