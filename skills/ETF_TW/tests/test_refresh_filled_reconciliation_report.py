from pathlib import Path
import importlib.util
import tempfile
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/refresh_filled_reconciliation_report.py")
spec = importlib.util.spec_from_file_location("refresh_filled_reconciliation_report", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_refresh_reconciliation_report_creates_state_file():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        (state_dir / "fills_ledger.json").write_text(json.dumps({
            "fills": [{
                "order_id": "fd-001",
                "symbol": "00922",
                "status": "filled",
                "filled_quantity": 1000,
            }]
        }), encoding="utf-8")
        (state_dir / "positions.json").write_text(json.dumps({
            "positions": []
        }), encoding="utf-8")

        out = module.refresh_reconciliation_report(state_dir)
        assert out["ok"] is False
        saved = json.loads((state_dir / "filled_reconciliation.json").read_text(encoding="utf-8"))
        assert saved["unreconciled_symbols"] == ["00922"]
