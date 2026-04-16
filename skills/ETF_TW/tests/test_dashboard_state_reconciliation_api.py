from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_api_exposes_state_reconciliation_block():
    body = module.overview_api()
    assert "state_reconciliation" in body
    recon = body["state_reconciliation"]
    assert "positions_vs_snapshot_match" in recon
    assert "open_orders_not_in_positions" in recon
