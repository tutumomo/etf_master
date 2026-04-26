from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_api_contains_watchlist_rows():
    body = module.overview_api()
    assert 'watchlist_rows' in body
    assert isinstance(body['watchlist_rows'], list)


def test_watchlist_catalog_includes_universe_only_bond_etf():
    catalog = module.load_etf_catalog()

    assert "00720B" in catalog
    item = module.build_watchlist_item("00720B", catalog["00720B"])
    assert item["name"] == "元大投資級公司債"
    assert item["group"] == "defensive"


def test_add_watchlist_symbol_accepts_universe_only_etf(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "STATE", tmp_path)
    monkeypatch.setattr(module, "refresh_monitoring_state", lambda: {"ok": True})

    result = module.add_watchlist_symbol("00720B")

    assert result["ok"] is True
    assert result["symbol"] == "00720B"
    saved = module.read_watchlist_state()
    assert saved["items"][0]["symbol"] == "00720B"
    assert saved["items"][0]["group"] == "defensive"
