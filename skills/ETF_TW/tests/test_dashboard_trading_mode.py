from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_classify_position_record_marks_live_zero_qty_as_broker_record():
    record = {
        "symbol": "0050",
        "quantity": 0,
        "source": "live_broker",
        "average_cost": 74.65,
        "unrealized_pnl": -187.0,
    }
    result = module.classify_position_record(record)
    assert result["holding_status"] == "券商回傳紀錄"
    assert result["needs_review"] is True


def test_build_trading_mode_summary_contains_mode_account_and_source():
    summary = module.build_trading_mode_summary({
        "effective_mode": "live-ready",
        "default_account": "sinopac_01",
        "default_broker": "sinopac",
        "data_source": "live_broker",
        "health_check_ok": True,
        "updated_at": "2026-03-30T19:00:00",
    })
    assert summary["mode_label"] == "LIVE-READY"
    assert summary["default_account"] == "sinopac_01"
    assert summary["data_source"] == "live_broker"


def test_build_trading_mode_warnings_detects_broker_records_needing_review():
    warnings = module.build_trading_mode_warnings(
        {"effective_mode": "live-ready", "data_source": "live_broker"},
        {"source": "live_broker"},
        [{"symbol": "0050", "holding_status": "券商回傳紀錄", "needs_review": True}],
    )
    assert any("券商回傳紀錄" in w for w in warnings)


def test_classify_position_record_maps_live_average_price_as_broker_record():
    record = {
        "symbol": "00878",
        "quantity": 0,
        "source": "live_broker",
        "average_price": 22.42,
        "market_value": 0.0,
        "unrealized_pnl": -36.0,
    }
    result = module.classify_position_record(record)
    assert result["needs_review"] is True
