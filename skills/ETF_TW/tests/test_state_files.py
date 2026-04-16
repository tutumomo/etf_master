import json
import sys
from pathlib import Path

# Add project root to path for core logic access
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

STATE = context.get_state_dir()


def test_state_files_exist_and_contain_valid_json():
    names = [
        "positions.json",
        "account_snapshot.json",
        "orders_open.json",
        "watchlist.json",
        "market_cache.json",
        "strategy_link.json",
    ]
    for name in names:
        path = STATE / name
        assert path.exists(), f"missing {name} in {STATE}"
        json.loads(path.read_text(encoding="utf-8"))
