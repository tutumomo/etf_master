from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/filled_reconciliation.py")
spec = importlib.util.spec_from_file_location("filled_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_collect_unreconciled_filled_symbols_detects_fill_without_position():
    fills_payload = {
        "fills": [{
            "order_id": "fd-001",
            "symbol": "00922",
            "status": "filled",
            "filled_quantity": 1000,
        }]
    }
    positions_payload = {
        "positions": []
    }
    result = module.collect_unreconciled_filled_symbols(fills_payload, positions_payload)
    assert result == ["00922"]


def test_collect_unreconciled_filled_symbols_ignores_symbols_already_in_positions():
    fills_payload = {
        "fills": [{
            "order_id": "fd-001",
            "symbol": "00922",
            "status": "filled",
            "filled_quantity": 1000,
        }]
    }
    positions_payload = {
        "positions": [{
            "symbol": "00922",
            "quantity": 1000,
        }]
    }
    result = module.collect_unreconciled_filled_symbols(fills_payload, positions_payload)
    assert result == []
