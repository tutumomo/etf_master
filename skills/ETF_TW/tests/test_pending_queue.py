"""
Tests for auto_trade.pending_queue
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts.auto_trade import pending_queue as pq

TW_TZ = ZoneInfo("Asia/Taipei")


@pytest.fixture
def tmp_paths(tmp_path):
    return {
        "queue": tmp_path / "pending.json",
        "history": tmp_path / "history.jsonl",
    }


def test_enqueue_basic(tmp_paths):
    sig = pq.enqueue(
        queue_path=tmp_paths["queue"],
        history_path=tmp_paths["history"],
        side="buy",
        symbol="00923",
        quantity=100,
        price=34.39,
        trigger_source="buy_scanner_0930",
        trigger_reason="VWAP 跌 2.13%",
    )
    assert sig["id"]
    assert sig["status"] == "pending"
    assert sig["symbol"] == "00923"
    assert sig["quantity"] == 100
    assert sig["ttl_minutes"] == pq.DEFAULT_TTL_MINUTES

    # queue file
    items = json.loads(tmp_paths["queue"].read_text(encoding="utf-8"))
    assert len(items) == 1
    assert items[0]["id"] == sig["id"]

    # history file
    lines = tmp_paths["history"].read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["_event"] == "enqueued"


def test_enqueue_invalid_side(tmp_paths):
    with pytest.raises(ValueError):
        pq.enqueue(
            queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
            side="hold", symbol="0050", quantity=1, price=100,
            trigger_source="x", trigger_reason="y",
        )


def test_enqueue_invalid_order_type(tmp_paths):
    with pytest.raises(ValueError):
        pq.enqueue(
            queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
            side="buy", symbol="0050", quantity=1, price=100,
            order_type="stop_loss",
            trigger_source="x", trigger_reason="y",
        )


def test_list_active_filters_expired_and_non_pending(tmp_paths):
    base_time = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    # 一筆未過期 pending
    s1 = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y",
        now=base_time,
    )
    # 一筆已過期 pending（手動竄改 expires_at 到過去）
    s2 = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0056", quantity=20, price=40,
        trigger_source="x", trigger_reason="y",
        now=base_time - timedelta(hours=1),
        ttl_minutes=15,
    )
    # 一筆已 acked（不該出現在 list_active）
    pq.update_status(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        signal_id=s1["id"], new_status="acked",
        now=base_time,
    )

    # active list 此時應該空（s1 已 acked、s2 已過期）
    active = pq.list_active(tmp_paths["queue"], now=base_time)
    assert active == []

    # 新增一筆當下入隊，list_active 應有 1 筆
    s3 = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="00878", quantity=50, price=24,
        trigger_source="x", trigger_reason="y",
        now=base_time,
    )
    active = pq.list_active(tmp_paths["queue"], now=base_time)
    assert len(active) == 1
    assert active[0]["id"] == s3["id"]
    assert active[0]["seconds_left"] > 0


def test_update_status_writes_history(tmp_paths):
    s = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y",
    )
    updated = pq.update_status(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        signal_id=s["id"], new_status="executed",
        extra={"order_no": "TW-12345"},
    )
    assert updated["status"] == "executed"
    assert updated["status_extra"]["order_no"] == "TW-12345"

    # history 應有 2 筆（enqueued + status_changed_to_executed）
    lines = tmp_paths["history"].read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    rec = json.loads(lines[1])
    assert rec["_event"] == "status_changed_to_executed"


def test_update_status_unknown_id(tmp_paths):
    res = pq.update_status(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        signal_id="not-exists", new_status="acked",
    )
    assert res is None


def test_update_status_invalid_status(tmp_paths):
    s = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y",
    )
    with pytest.raises(ValueError):
        pq.update_status(
            queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
            signal_id=s["id"], new_status="finished",
        )


def test_expire_old(tmp_paths):
    base_time = datetime(2026, 4, 25, 9, 30, tzinfo=TW_TZ)
    # 兩筆訊號：一筆已過期、一筆未過期
    s_old = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y",
        now=base_time - timedelta(minutes=20),
    )
    s_new = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0056", quantity=20, price=40,
        trigger_source="x", trigger_reason="y",
        now=base_time,
    )

    expired = pq.expire_old(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        now=base_time,
    )
    assert s_old["id"] in expired
    assert s_new["id"] not in expired

    # 確認 queue 中 s_old.status='expired'，s_new.status='pending'
    items = json.loads(tmp_paths["queue"].read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in items}
    assert by_id[s_old["id"]]["status"] == "expired"
    assert by_id[s_new["id"]]["status"] == "pending"


def test_sum_today_buy_amount(tmp_paths):
    today = datetime.now(tz=TW_TZ)
    pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=100, price=86,
        trigger_source="x", trigger_reason="y",
        now=today,
    )
    pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0056", quantity=200, price=40,
        trigger_source="x", trigger_reason="y",
        now=today,
    )
    # 加一筆 sell（不該被算入）
    pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="sell", symbol="0050", quantity=50, price=86,
        trigger_source="x", trigger_reason="y",
        now=today,
    )

    total = pq.sum_today_buy_amount(tmp_paths["queue"])
    assert total == pytest.approx(100 * 86 + 200 * 40)  # 16600


def test_sum_today_buy_amount_excludes_rejected(tmp_paths):
    today = datetime.now(tz=TW_TZ)
    s = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=100, price=86,
        trigger_source="x", trigger_reason="y",
        now=today,
    )
    # rejected 應該不算
    pq.update_status(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        signal_id=s["id"], new_status="rejected",
    )
    total = pq.sum_today_buy_amount(tmp_paths["queue"])
    assert total == 0


def test_get_by_id(tmp_paths):
    s = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y",
    )
    found = pq.get_by_id(tmp_paths["queue"], s["id"])
    assert found is not None
    assert found["id"] == s["id"]
    assert pq.get_by_id(tmp_paths["queue"], "non-exist") is None


def test_count_by_status(tmp_paths):
    today = datetime.now(tz=TW_TZ)
    s1 = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0050", quantity=10, price=86,
        trigger_source="x", trigger_reason="y", now=today,
    )
    s2 = pq.enqueue(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        side="buy", symbol="0056", quantity=20, price=40,
        trigger_source="x", trigger_reason="y", now=today,
    )
    pq.update_status(
        queue_path=tmp_paths["queue"], history_path=tmp_paths["history"],
        signal_id=s1["id"], new_status="executed",
    )
    counts = pq.count_by_status(tmp_paths["queue"])
    assert counts["pending"] == 1
    assert counts["executed"] == 1
