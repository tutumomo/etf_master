from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/write_layered_review_plan.py")
spec = importlib.util.spec_from_file_location("write_layered_review_plan", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_write_layered_review_plan_writes_state_and_ledger():
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        payload = module.write_layered_review_plan(state_dir, request_id='req-write-001')
        assert payload['request_id'] == 'req-write-001'

        state_payload = json.loads((state_dir / 'layered_review_plan.json').read_text(encoding='utf-8'))
        assert state_payload['request_id'] == 'req-write-001'

        ledger_lines = (state_dir / 'layered_review_plan.jsonl').read_text(encoding='utf-8').strip().splitlines()
        assert len(ledger_lines) == 1
