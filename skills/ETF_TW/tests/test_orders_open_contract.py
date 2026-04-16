from pathlib import Path
import json

INSTANCE_ORDERS_OPEN = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/orders_open.json")
VALID_STATUSES = {"pending", "submitted", "filled", "cancelled", "rejected"}
REQUIRED_ORDER_FIELDS = {
    "order_id",
    "symbol",
    "action",
    "quantity",
    "mode",
    "status",
    "source",
}
OPTIONAL_BROKER_FIELDS = {"ordno", "seqno", "account", "account_id", "broker_id", "price", "order_lot", "order_type", "price_type", "name"}


def test_orders_open_file_contains_valid_shape():
    payload = json.loads(INSTANCE_ORDERS_OPEN.read_text(encoding="utf-8"))
    assert "orders" in payload
    assert "updated_at" in payload
    assert "source" in payload
    assert isinstance(payload["orders"], list)


def test_orders_open_rows_follow_minimum_contract():
    payload = json.loads(INSTANCE_ORDERS_OPEN.read_text(encoding="utf-8"))
    for row in payload["orders"]:
        assert REQUIRED_ORDER_FIELDS.issubset(row.keys())
        assert row["status"] in VALID_STATUSES
        assert row["source"] in {"live_broker", "paper_ledger"}
        assert isinstance(row["quantity"], int)
        unknown_keys = set(row.keys()) - REQUIRED_ORDER_FIELDS - OPTIONAL_BROKER_FIELDS
        assert "updated_at" not in row
        assert len(unknown_keys) == 0, f"Unexpected keys in orders_open row: {unknown_keys}"


def test_orders_open_submitted_rows_do_not_require_fill_only_fields():
    payload = json.loads(INSTANCE_ORDERS_OPEN.read_text(encoding="utf-8"))
    for row in payload["orders"]:
        if row["status"] == "submitted":
            assert "filled_quantity" not in row
            assert "filled_price" not in row
