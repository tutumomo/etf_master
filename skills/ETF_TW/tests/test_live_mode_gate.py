"""
Live 模式授權閘門 contract tests — LIVE-02
Tests: 7 (status + unlock double-confirm + quality gate + idempotency)
"""
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fastapi.testclient import TestClient

# Import app and the context module used by the endpoints
from dashboard.app import app
from scripts.etf_core import context as _ctx

CONFIRM_1 = "ENABLE LIVE TRADING"
CONFIRM_2 = "I UNDERSTAND REAL MONEY IS AT RISK"

client = TestClient(app)


def _write_backtest(tmp_path: Path, quality_gate_passed: bool) -> None:
    data = {
        "quality_gate_passed": quality_gate_passed,
        "win_rate": 0.55 if quality_gate_passed else 0.40,
        "max_drawdown": 0.10 if quality_gate_passed else 0.20,
        "last_updated": "2025-01-01T00:00:00+08:00",
    }
    (tmp_path / "backtest_results.json").write_text(json.dumps(data))


# ── Test 1 ──────────────────────────────────────────────────────────────────

def test_status_returns_paper_by_default(tmp_path, monkeypatch):
    """No state files → enabled=False, quality_gate_passed=False."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    resp = client.get("/api/live-mode/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["quality_gate_passed"] is False


# ── Test 2 ──────────────────────────────────────────────────────────────────

def test_status_reflects_quality_gate_true(tmp_path, monkeypatch):
    """backtest_results.json quality_gate_passed=True → status returns True."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=True)
    resp = client.get("/api/live-mode/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["quality_gate_passed"] is True
    assert data["backtest_summary"]["win_rate"] == pytest.approx(0.55)


# ── Test 3 ──────────────────────────────────────────────────────────────────

def test_unlock_wrong_confirm_1_returns_400(tmp_path, monkeypatch):
    """Wrong confirm_1 → 400."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=True)
    resp = client.post(
        "/api/live-mode/unlock",
        json={"confirm_1": "wrong string", "confirm_2": CONFIRM_2},
    )
    assert resp.status_code == 400


# ── Test 4 ──────────────────────────────────────────────────────────────────

def test_unlock_wrong_confirm_2_returns_400(tmp_path, monkeypatch):
    """Correct confirm_1 but wrong confirm_2 → 400."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=True)
    resp = client.post(
        "/api/live-mode/unlock",
        json={"confirm_1": CONFIRM_1, "confirm_2": "nope"},
    )
    assert resp.status_code == 400


# ── Test 5 ──────────────────────────────────────────────────────────────────

def test_unlock_quality_gate_not_passed_returns_403(tmp_path, monkeypatch):
    """Correct confirms, but quality gate not passed → 403."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=False)
    resp = client.post(
        "/api/live-mode/unlock",
        json={"confirm_1": CONFIRM_1, "confirm_2": CONFIRM_2},
    )
    assert resp.status_code == 403


# ── Test 6 ──────────────────────────────────────────────────────────────────

def test_unlock_success_writes_live_mode_json(tmp_path, monkeypatch):
    """Correct confirms + quality_gate_passed=True → 200, live_mode.json written."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=True)
    resp = client.post(
        "/api/live-mode/unlock",
        json={"confirm_1": CONFIRM_1, "confirm_2": CONFIRM_2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["enabled"] is True

    live_mode_path = tmp_path / "live_mode.json"
    assert live_mode_path.exists(), "live_mode.json must be written"
    written = json.loads(live_mode_path.read_text())
    assert written["enabled"] is True
    assert written["quality_gate_passed_at_unlock"] is True
    assert written["unlocked_by"] == "dashboard"
    assert "unlocked_at" in written


# ── Test 7 ──────────────────────────────────────────────────────────────────

def test_unlock_idempotent(tmp_path, monkeypatch):
    """Unlock twice with correct inputs → second call also 200."""
    monkeypatch.setattr(_ctx, "get_state_dir", lambda: tmp_path)
    _write_backtest(tmp_path, quality_gate_passed=True)
    payload = {"confirm_1": CONFIRM_1, "confirm_2": CONFIRM_2}
    resp1 = client.post("/api/live-mode/unlock", json=payload)
    assert resp1.status_code == 200
    resp2 = client.post("/api/live-mode/unlock", json=payload)
    assert resp2.status_code == 200
