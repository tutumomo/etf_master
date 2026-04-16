from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_cron_registry.py")
spec = importlib.util.spec_from_file_location("layered_review_cron_registry", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_compute_jobs_to_add_filters_existing_dedupe_keys():
    jobs = [
        {'metadata': {'dedupe_key': 'req-1::early_review'}},
        {'metadata': {'dedupe_key': 'req-1::short_review'}},
        {'metadata': {'dedupe_key': 'req-1::mid_review'}},
    ]
    existing = {'req-1::short_review'}
    pending = module.compute_jobs_to_add(jobs, existing)
    assert len(pending) == 2
    keys = [job['metadata']['dedupe_key'] for job in pending]
    assert 'req-1::short_review' not in keys
