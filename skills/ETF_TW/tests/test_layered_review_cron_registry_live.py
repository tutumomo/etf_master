from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_cron_registry_live.py")
spec = importlib.util.spec_from_file_location("layered_review_cron_registry_live", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_extract_dedupe_keys_from_cron_list_payload():
    payload = [
        {'job': {'metadata': {'dedupe_key': 'req-a::early_review'}}},
        {'job': {'metadata': {'dedupe_key': 'req-a::short_review'}}},
    ]
    keys = module.extract_dedupe_keys_from_cron_list(payload)
    assert keys == {'req-a::early_review', 'req-a::short_review'}
