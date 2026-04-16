from pathlib import Path
import importlib.util
import json
import tempfile
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/auto_quality_refresh.py")
spec = importlib.util.spec_from_file_location("auto_quality_refresh", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_auto_refresh_quality_state_writes_ai_decision_quality_json():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d/'ai_decision_reflection.jsonl').write_text(
            json.dumps({"request_id":"a","action":"preview_buy","review_status":"reviewed"}, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )
        payload = module.auto_refresh_quality_state(d)
        assert payload['source'] == 'ai_decision_quality_state'
        written = json.loads((d/'ai_decision_quality.json').read_text(encoding='utf-8'))
        assert written['updated_at'] == payload['updated_at']
