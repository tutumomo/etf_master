from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_paper_state.py")
spec = importlib.util.spec_from_file_location("sync_paper_state", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_positions_from_trades_aggregates_buys_and_sells():
    trades = [
        {"symbol": "0050", "side": "buy", "quantity": 100, "estimated_total_cost": 1000},
        {"symbol": "0050", "side": "buy", "quantity": 100, "estimated_total_cost": 1200},
        {"symbol": "0050", "side": "sell", "quantity": 50, "estimated_total_cost": 600},
    ]
    positions = module.build_positions_from_trades(trades)
    assert positions[0]["symbol"] == "0050"
    assert positions[0]["quantity"] == 150
