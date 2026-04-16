from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_classify_freshness_without_timestamp_returns_warn_like_unknown():
    freshness = module.classify_freshness(None)
    assert freshness["label"] == "unknown"


def test_build_risk_signals_returns_list():
    signals = module.build_risk_signals([], {"updated_at": None}, {"orders": []})
    assert isinstance(signals, list)
    assert len(signals) >= 2
