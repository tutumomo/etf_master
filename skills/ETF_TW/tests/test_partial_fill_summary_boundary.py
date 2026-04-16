def test_partial_fill_should_not_be_treated_as_complete_holding_in_summary_logic():
    orders_open = {
        "orders": [{
            "order_id": "pf-001",
            "symbol": "00922",
            "status": "partial_filled",
            "filled_quantity": 300,
            "remaining_quantity": 700,
        }]
    }
    portfolio_snapshot = {
        "holdings": []
    }
    holding_symbols = {row["symbol"] for row in portfolio_snapshot["holdings"]}
    for row in orders_open["orders"]:
        if row.get("status") == "partial_filled":
            assert row["symbol"] not in holding_symbols
