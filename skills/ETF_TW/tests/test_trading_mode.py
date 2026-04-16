from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/trading_mode.py")
spec = importlib.util.spec_from_file_location("trading_mode", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_has_live_credentials_false_when_missing_keys():
    config = {"accounts": {"sinopac_01": {"mode": "live"}}}
    assert module.has_live_credentials(config) is False


def test_has_live_credentials_true_when_live_account_has_credentials():
    config = {
        "accounts": {
            "sinopac_01": {
                "mode": "live",
                "credentials": {"api_key": "k", "api_secret": "s"},
                "account_id": "0737121",
            }
        }
    }
    assert module.has_live_credentials(config) is True


def test_resolve_effective_mode_returns_paper_without_live_credentials():
    result = module.resolve_effective_mode(config={}, manual_override=None, live_check_ok=False, previous_mode="paper")
    assert result["effective_mode"] == "paper"
    assert result["live_capable"] is False


def test_resolve_effective_mode_returns_live_ready_when_credentials_and_health_ok():
    config = {
        "accounts": {
            "sinopac_01": {
                "mode": "live",
                "credentials": {"api_key": "k", "api_secret": "s"},
                "account_id": "0737121",
            }
        }
    }
    result = module.resolve_effective_mode(config=config, manual_override=None, live_check_ok=True, previous_mode="paper")
    assert result["effective_mode"] == "live-ready"
    assert result["live_capable"] is True
    assert result["health_check_ok"] is True


def test_manual_override_paper_wins():
    config = {
        "accounts": {
            "sinopac_01": {
                "mode": "live",
                "credentials": {"api_key": "k", "api_secret": "s"},
                "account_id": "0737121",
            }
        }
    }
    result = module.resolve_effective_mode(config=config, manual_override="paper", live_check_ok=True, previous_mode="live-ready")
    assert result["effective_mode"] == "paper"
    assert result["manual_override"] == "paper"


def test_manual_override_live_with_failed_health_keeps_previous_mode():
    config = {
        "accounts": {
            "sinopac_01": {
                "mode": "live",
                "credentials": {"api_key": "k", "api_secret": "s"},
                "account_id": "0737121",
            }
        }
    }
    result = module.resolve_effective_mode(config=config, manual_override="live", live_check_ok=False, previous_mode="paper")
    assert result["effective_mode"] == "paper"
    assert result["manual_override"] == "live"
    assert result["health_check_ok"] is False
