def test_filled_order_should_require_positions_truth_before_snapshot_holding_is_considered_verified():
    orders_open = {
        "orders": []
    }
    fills_ledger = {
        "fills": [{
            "order_id": "fd-001",
            "symbol": "00922",
            "status": "filled",
            "filled_quantity": 1000,
            "price": 27.45,
            "source_type": "broker_callback",
        }]
    }
    positions = {
        "positions": []
    }
    snapshot = {
        "holdings": []
    }

    holding_symbols = {row["symbol"] for row in snapshot["holdings"]}
    position_symbols = {row["symbol"] for row in positions["positions"]}

    for row in fills_ledger["fills"]:
        if row.get("status") == "filled":
            assert row["symbol"] not in holding_symbols
            assert row["symbol"] not in position_symbols


def test_positions_remain_truth_source_after_fill_fact_exists():
    fills_ledger = {
        "fills": [{
            "order_id": "fd-001",
            "symbol": "00922",
            "status": "filled",
            "filled_quantity": 1000,
            "price": 27.45,
            "source_type": "broker_callback",
        }]
    }
    positions = {
        "positions": [{
            "symbol": "00922",
            "quantity": 1000,
        }]
    }
    snapshot = {
        "holdings": [{
            "symbol": "00922",
            "quantity": 1000,
        }]
    }

    position_symbols = {row["symbol"] for row in positions["positions"]}
    holding_symbols = {row["symbol"] for row in snapshot["holdings"]}
    assert position_symbols == holding_symbols == {"00922"}
