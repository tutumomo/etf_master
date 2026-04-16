from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_cron_jobs.py")
spec = importlib.util.spec_from_file_location("layered_review_cron_jobs", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_cron_job_payloads_creates_agent_turn_jobs():
    rows = [
        {
            'request_id': 'req-job-001',
            'review_window': 'early_review',
            'review_window_label': 'T+1 早期復盤',
            'offset_trading_days': 1,
            'runner': 'scripts/auto_post_review_cycle.py',
            'dedupe_key': 'req-job-001::early_review',
            'status': 'draft',
        }
    ]
    jobs = module.build_cron_job_payloads(rows, session_target='isolated')
    assert len(jobs) == 1
    job = jobs[0]
    assert job['sessionTarget'] == 'isolated'
    assert job['payload']['kind'] == 'agentTurn'
    assert 'req-job-001' in job['payload']['message']
    assert 'early_review' in job['payload']['message']
    assert job['delivery']['mode'] == 'announce'
