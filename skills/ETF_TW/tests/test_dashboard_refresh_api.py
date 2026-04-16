from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py")
spec = importlib.util.spec_from_file_location("dashboard_app", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_refresh_dashboard_state_success_path(monkeypatch):
    monkeypatch.setattr(module, "refresh_monitoring_state", lambda: {
        "ok": True,
        "returncode": 0,
        "stdout": "MONITORING_REFRESH_OK",
        "stderr": "",
    })
    body = module.refresh_dashboard_state()
    assert body["ok"] is True
    assert body["message"] == "資料已完成更新"


def test_refresh_dashboard_state_failure_raises_http_exception(monkeypatch):
    monkeypatch.setattr(module, "refresh_monitoring_state", lambda: {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "Command failed with exit status 1",
    })
    try:
        module.refresh_dashboard_state()
        assert False, "Expected exception"
    except module.HTTPException as e:
        assert e.status_code == 500
        assert "資料更新失敗" in e.detail
        assert "exit status 1" in e.detail
