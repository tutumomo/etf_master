from pathlib import Path
import json

POSITIONS_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/positions.json")
SNAPSHOT_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/portfolio_snapshot.json")
ORDERS_OPEN_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/instances/etf_master/state/orders_open.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_open_orders_symbols_do_not_appear_in_positions_until_filled():
    positions = load(POSITIONS_PATH)
    orders_open = load(ORDERS_OPEN_PATH)
    position_symbols = {row["symbol"] for row in positions.get("positions", [])}

    for row in orders_open.get("orders", []):
        if row.get("status") == "submitted":
            assert row["symbol"] not in position_symbols, (
                f"submitted order symbol {row['symbol']} should not appear in positions before fill"
            )


def test_open_orders_symbols_do_not_force_holdings_into_snapshot_until_filled():
    snapshot = load(SNAPSHOT_PATH)
    orders_open = load(ORDERS_OPEN_PATH)
    holding_symbols = {row["symbol"] for row in snapshot.get("holdings", [])}

    for row in orders_open.get("orders", []):
        if row.get("status") == "submitted":
            assert row["symbol"] not in holding_symbols, (
                f"submitted order symbol {row['symbol']} should not appear in portfolio holdings before fill"
            )


def test_positions_and_snapshot_symbols_remain_aligned_for_live_holdings():
    positions = load(POSITIONS_PATH)
    snapshot = load(SNAPSHOT_PATH)
    position_symbols = {row["symbol"] for row in positions.get("positions", [])}
    holding_symbols = {row["symbol"] for row in snapshot.get("holdings", [])}
    assert position_symbols == holding_symbols
