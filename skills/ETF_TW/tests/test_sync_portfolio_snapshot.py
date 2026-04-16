from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_portfolio_snapshot.py")
spec = importlib.util.spec_from_file_location("sync_portfolio_snapshot", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_snapshot_from_memory_extracts_holdings_and_cash():
    text = """**0050**：持有 **203 股**，成本 **74.65**，現價 **75.0**
**00878**：持有 **100 股**，成本 **22.42**，現價 **22.39**
**帳戶餘額**：30,000 元
**持倉總市值**：17,464 元
**帳面總資產**：約 47,464 元"""
    payload = module.build_snapshot_from_memory(text)
    assert payload['cash'] == 30000
    assert payload['market_value'] == 17464
    assert payload['total_equity'] == 47464
    assert len(payload['holdings']) == 2
