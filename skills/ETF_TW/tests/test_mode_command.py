from pathlib import Path
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import etf_tw as module


def test_format_mode_status_contains_required_fields():
    text = module.format_mode_status({
        "effective_mode": "live-ready",
        "default_account": "sinopac_01",
        "data_source": "live_broker",
        "health_check_ok": True,
    })
    assert "目前模式" in text
    assert "預設帳戶" in text
    assert "資料來源" in text
    assert "health check" in text
