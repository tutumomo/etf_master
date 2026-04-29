import importlib.util
import os
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "dashboard" / "app.py"
TEMPLATE_PATH = ROOT / "dashboard" / "templates" / "overview.html"


def _load_dashboard_app():
    if not os.environ.get("AGENT_ID") and not os.environ.get("OPENCLAW_AGENT_NAME"):
        os.environ["AGENT_ID"] = "etf_master"
    spec = importlib.util.spec_from_file_location("dashboard_app_phase2_dca", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase2_dca_start_writes_state(tmp_path):
    module = _load_dashboard_app()
    original_state = module.STATE
    module.STATE = tmp_path
    try:
        payload = module.Phase2DcaStartRequest(
            total_target_twd=12000,
            target_days=12,
            symbol_priority=["0050", "00878.TW"],
        )
        body = module.phase2_start_dca(payload)
    finally:
        module.STATE = original_state

    assert body["ok"] is True
    assert body["dca"]["enabled"] is True
    assert body["dca"]["total_target_twd"] == 12000
    assert body["dca"]["target_days"] == 12
    assert body["dca"]["symbol_priority"] == ["0050", "00878"]


def test_phase2_dca_start_rejects_empty_symbols(tmp_path):
    module = _load_dashboard_app()
    original_state = module.STATE
    module.STATE = tmp_path
    try:
        payload = module.Phase2DcaStartRequest(
            total_target_twd=12000,
            target_days=12,
            symbol_priority=[],
        )
        with pytest.raises(HTTPException) as exc:
            module.phase2_start_dca(payload)
    finally:
        module.STATE = original_state

    assert exc.value.status_code == 400
    assert "至少一個" in exc.value.detail


def test_phase2_dca_stop_disables_state(tmp_path):
    module = _load_dashboard_app()
    original_state = module.STATE
    module.STATE = tmp_path
    try:
        module.phase2_start_dca(
            module.Phase2DcaStartRequest(
                total_target_twd=12000,
                target_days=12,
                symbol_priority=["0050"],
            )
        )
        body = module.phase2_stop_dca()
    finally:
        module.STATE = original_state

    assert body["ok"] is True
    assert body["dca"]["enabled"] is False
    assert body["dca"]["total_target_twd"] == 12000


def test_dashboard_template_contains_phase2_dca_controls():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "phase2DcaStart" in text
    assert "phase2DcaStop" in text
    assert "/api/auto-trade/phase2/dca/start" in text
    assert "/api/auto-trade/phase2/dca/stop" in text
    assert "dca_total_target_twd" in text
    assert "dca_symbol_priority" in text
