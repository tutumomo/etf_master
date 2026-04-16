from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/layered_review_cron_draft.py")
spec = importlib.util.spec_from_file_location("layered_review_cron_draft", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_cron_jobs_from_plan_returns_three_jobs():
    plan = {
        'request_id': 'req-cron-001',
        'windows': [
            {'name': 'early_review', 'label': 'T+1 早期復盤', 'offset_trading_days': 1},
            {'name': 'short_review', 'label': 'T+3 短期復盤', 'offset_trading_days': 3},
            {'name': 'mid_review', 'label': 'T+10 中期復盤', 'offset_trading_days': 10},
        ],
        'binding': {'runner': 'scripts/auto_post_review_cycle.py'}
    }
    jobs = module.build_layered_review_cron_jobs(plan)
    assert len(jobs) == 3
    assert jobs[0]['request_id'] == 'req-cron-001'
    assert jobs[0]['review_window'] == 'early_review'
    assert jobs[2]['offset_trading_days'] == 10
