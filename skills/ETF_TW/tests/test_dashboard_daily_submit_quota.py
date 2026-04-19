import json
import os
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "dashboard" / "app.py"
TEMPLATE_PATH = ROOT / "dashboard" / "templates" / "overview.html"
TW_TZ = ZoneInfo("Asia/Taipei")
TODAY = datetime.now(TW_TZ).date().isoformat()
NOW_STR = datetime.now(TW_TZ).isoformat()


def _load_dashboard_app():
    if not os.environ.get("AGENT_ID") and not os.environ.get("OPENCLAW_AGENT_NAME"):
        os.environ["AGENT_ID"] = "etf_master"
    spec = importlib.util.spec_from_file_location("dashboard_app_daily_submit_quota", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safety_redlines_request_accepts_daily_submit_quota_fields():
    module = _load_dashboard_app()
    payload = module.SafetyRedlinesRequest(
        max_buy_amount_twd=500000.0,
        max_buy_amount_pct=20.0,
        max_buy_shares=200,
        max_concentration_pct=30.0,
        daily_loss_limit_pct=-3.0,
        ai_confidence_threshold=0.7,
        daily_max_buy_submits=2,
        daily_max_sell_submits=2,
        enabled=True,
    )

    assert payload.daily_max_buy_submits == 2
    assert payload.daily_max_sell_submits == 2


def test_build_overview_model_exposes_daily_submit_quota_state(tmp_path):
    module = _load_dashboard_app()
    original_state = module.STATE
    module.STATE = tmp_path
    try:
        (tmp_path / "safety_redlines.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "max_buy_amount_twd": 500000.0,
                    "max_buy_amount_pct": 20.0,
                    "max_buy_shares": 200,
                    "max_concentration_pct": 30.0,
                    "daily_loss_limit_pct": -3.0,
                    "ai_confidence_threshold": 0.7,
                    "daily_max_buy_submits": 2,
                    "daily_max_sell_submits": 2,
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "daily_order_limits.json").write_text(
            json.dumps(
                {
                    "date": TODAY,
                    "buy_submit_count": 1,
                    "sell_submit_count": 0,
                    "last_updated": NOW_STR,
                }
            ),
            encoding="utf-8",
        )

        overview = module.build_overview_model()
    finally:
        module.STATE = original_state

    assert overview["safety_redlines"]["daily_max_buy_submits"] == 2
    assert overview["safety_redlines"]["daily_max_sell_submits"] == 2
    assert overview["daily_order_limits"]["buy_submit_count"] == 1
    assert overview["daily_order_limits"]["sell_submit_count"] == 0


def test_dashboard_template_contains_daily_submit_quota_controls():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "每日可下單買入次數" in text
    assert "每日可下單賣出次數" in text
    assert "今日買入送單次數" in text
    assert "今日賣出送單次數" in text
    assert "redline_daily_max_buy_submits" in text
    assert "redline_daily_max_sell_submits" in text
    assert "daily_max_buy_submits:" in text
    assert "daily_max_sell_submits:" in text
