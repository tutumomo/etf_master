import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.daily_order_limits import (
    default_daily_order_limits,
    ensure_daily_order_limits,
    increment_daily_submit_count,
)
from scripts.sync_daily_pnl import DEFAULT_REDLINES


def test_default_redlines_include_daily_submit_quota_fields():
    assert DEFAULT_REDLINES["daily_max_buy_submits"] == 2
    assert DEFAULT_REDLINES["daily_max_sell_submits"] == 2


def test_ensure_daily_order_limits_initializes_missing_file(tmp_path: Path):
    path = tmp_path / "daily_order_limits.json"

    data = ensure_daily_order_limits(path, today="2026-04-17")
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert data["buy_submit_count"] == 0
    assert data["sell_submit_count"] == 0
    assert persisted["buy_submit_count"] == 0
    assert persisted["sell_submit_count"] == 0


def test_ensure_daily_order_limits_preserves_same_day_counts(tmp_path: Path):
    path = tmp_path / "daily_order_limits.json"
    path.write_text(
        json.dumps(
            {
                "date": "2026-04-17",
                "buy_submit_count": 1,
                "sell_submit_count": 2,
                "last_updated": "2026-04-17T09:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )

    data = ensure_daily_order_limits(path, today="2026-04-17")

    assert data["buy_submit_count"] == 1
    assert data["sell_submit_count"] == 2


def test_ensure_daily_order_limits_resets_on_new_day(tmp_path: Path):
    path = tmp_path / "daily_order_limits.json"
    path.write_text(
        json.dumps(
            {
                "date": "2026-04-16",
                "buy_submit_count": 2,
                "sell_submit_count": 1,
                "last_updated": "2026-04-16T15:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )

    data = ensure_daily_order_limits(path, today="2026-04-17")

    assert data["buy_submit_count"] == 0
    assert data["sell_submit_count"] == 0


def test_increment_buy_submit_count(tmp_path: Path):
    path = tmp_path / "daily_order_limits.json"
    data = increment_daily_submit_count(path, "buy", today="2026-04-17")

    assert data["buy_submit_count"] == 1
    assert data["sell_submit_count"] == 0


def test_increment_sell_submit_count(tmp_path: Path):
    path = tmp_path / "daily_order_limits.json"
    data = increment_daily_submit_count(path, "sell", today="2026-04-17")

    assert data["buy_submit_count"] == 0
    assert data["sell_submit_count"] == 1


def test_default_daily_order_limits_shape():
    data = default_daily_order_limits(today="2026-04-17")

    assert set(data.keys()) == {
        "date",
        "buy_submit_count",
        "sell_submit_count",
        "last_updated",
    }
