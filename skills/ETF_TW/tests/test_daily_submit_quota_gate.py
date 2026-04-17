import json
import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.pre_flight_gate import check_order


def _write_daily_order_limits(
    tmp_path: Path,
    *,
    buy_submit_count: int = 0,
    sell_submit_count: int = 0,
) -> None:
    (tmp_path / "daily_order_limits.json").write_text(
        json.dumps(
            {
                "date": "2026-04-17",
                "buy_submit_count": buy_submit_count,
                "sell_submit_count": sell_submit_count,
                "last_updated": "2026-04-17T09:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )


def _base_safety_data():
    return {
        "redlines": {
            "enabled": True,
            "max_buy_amount_twd": 500000.0,
            "max_buy_shares": 200,
            "max_concentration_pct": 30.0,
            "ai_confidence_threshold": 0.7,
            "daily_max_buy_submits": 2,
            "daily_max_sell_submits": 2,
        },
        "pnl": {"circuit_breaker_triggered": False},
    }


def test_buy_submit_quota_blocks_at_limit(tmp_path: Path):
    _write_daily_order_limits(tmp_path, buy_submit_count=2)
    order = {"symbol": "0050", "side": "buy", "quantity": 100, "price": 150.0}
    context = {"force_trading_hours": False, "state_dir": tmp_path}

    with patch("scripts.pre_flight_gate.load_safety_data", return_value=_base_safety_data()):
        result = check_order(order, context)

    assert result["passed"] is False
    assert result["reason"] == "daily_buy_submit_quota_exceeded"
    assert result["details"]["limit"] == 2
    assert result["details"]["used"] == 2


def test_sell_submit_quota_blocks_at_limit(tmp_path: Path):
    _write_daily_order_limits(tmp_path, sell_submit_count=2)
    order = {"symbol": "0050", "side": "sell", "quantity": 100, "price": 150.0}
    context = {"force_trading_hours": False, "state_dir": tmp_path, "inventory": {"0050": 100}}

    with patch("scripts.pre_flight_gate.load_safety_data", return_value=_base_safety_data()):
        result = check_order(order, context)

    assert result["passed"] is False
    assert result["reason"] == "daily_sell_submit_quota_exceeded"
    assert result["details"]["limit"] == 2
    assert result["details"]["used"] == 2


def test_submit_quota_below_limit_allows_order(tmp_path: Path):
    _write_daily_order_limits(tmp_path, buy_submit_count=1)
    order = {"symbol": "0050", "side": "buy", "quantity": 100, "price": 150.0}
    context = {"force_trading_hours": False, "state_dir": tmp_path}

    with patch("scripts.pre_flight_gate.load_safety_data", return_value=_base_safety_data()):
        result = check_order(order, context)

    assert result["passed"] is True
