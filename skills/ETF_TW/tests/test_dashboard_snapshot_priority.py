from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_overview_api_uses_snapshot_backed_account_shape():
    body = module.overview_api()
    assert 'account' in body
    assert 'position_rows' in body
