from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_write_strategy_state_rejects_invalid_value():
    try:
        module.write_strategy_state("亂寫策略", "無")
    except ValueError as e:
        assert 'invalid base_strategy' in str(e)
    else:
        raise AssertionError('should reject invalid strategy')


def test_notify_helper_script_exists():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/notify_agent_strategy_change.py')
    assert path.exists()
