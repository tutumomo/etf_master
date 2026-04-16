from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/filled_reconciliation.py")
spec = importlib.util.spec_from_file_location("filled_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_reconciliation_report_includes_unreconciled_symbols():
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
    report = module.build_reconciliation_report(fills_payload, positions_payload)
    assert report["ok"] is False
    assert report["unreconciled_symbols"] == ["00922"]
    assert report["unreconciled_count"] == 1


def test_build_reconciliation_report_ok_when_positions_aligned():
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
    report = module.build_reconciliation_report(fills_payload, positions_payload)
    assert report["ok"] is True
    assert report["unreconciled_symbols"] == []
    assert report["unreconciled_count"] == 0
