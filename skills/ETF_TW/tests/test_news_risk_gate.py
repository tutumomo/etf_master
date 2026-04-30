"""
Tests for buy_scanner._news_risk_gate (F-news 接線):
  - 高風險訊號 → multiplier 0.5（haircut，不擋買）
  - 低/無訊號 → multiplier 1.0
  - 缺資料 → multiplier 1.0（向後相容）
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.auto_trade.buy_scanner import _news_risk_gate


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path


def _write_news(state_dir: Path, payload: dict) -> None:
    (state_dir / "news_intelligence_report.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )


def test_no_news_file_returns_allow(state_dir):
    """沒有 news_intelligence_report.json → multiplier=1.0（向後相容）"""
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == 1.0
    assert res["action"] == "allow"
    assert res["source"] == "missing_news_intelligence"


def test_low_signal_returns_allow(state_dir):
    """signal_strength=low → multiplier=1.0"""
    _write_news(state_dir, {"signal_strength": "low", "risk_flagged": 1})
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == 1.0
    assert res["action"] == "allow"
    assert res["signal_strength"] == "low"


def test_none_signal_returns_allow(state_dir):
    _write_news(state_dir, {"signal_strength": "none", "risk_flagged": 0})
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == 1.0


def test_medium_signal_haircut(state_dir):
    """signal_strength=medium → multiplier=0.7"""
    _write_news(state_dir, {"signal_strength": "medium", "risk_flagged": 2})
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == pytest.approx(0.7)
    assert res["action"] == "haircut"
    assert res["risk_flagged"] == 2


def test_high_signal_strong_haircut(state_dir):
    """signal_strength=high → multiplier=0.4"""
    _write_news(state_dir, {"signal_strength": "high", "risk_flagged": 5})
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == pytest.approx(0.4)
    assert res["action"] == "strong_haircut"
    assert res["risk_flagged"] == 5


def test_corrupted_payload_returns_allow(state_dir):
    """payload 結構壞掉 → 向後相容，不擋買"""
    (state_dir / "news_intelligence_report.json").write_text("not json", encoding="utf-8")
    res = _news_risk_gate(state_dir)
    assert res["multiplier"] == 1.0
