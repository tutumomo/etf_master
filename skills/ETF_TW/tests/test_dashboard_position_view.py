from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_position_view_includes_name_with_watchlist_or_etf_map():
    rows = module.build_position_view(
        {"positions": [{"symbol": "0050", "quantity": 100, "average_cost": 10, "total_cost": 1000, "source": "snapshot"}]},
        {"quotes": {"0050": {"current_price": 12}}},
        [{"symbol": "0050", "current_price": 12}],
        [{"symbol": "0050", "name": "元大台灣50"}],
    )
    assert rows[0]["name"] == "元大台灣50"
    assert rows[0]["market_value"] == 1200
