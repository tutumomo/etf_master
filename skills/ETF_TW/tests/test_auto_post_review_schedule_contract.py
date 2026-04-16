from pathlib import Path


def test_auto_post_review_cycle_script_exists_for_future_scheduler_hookup():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/auto_post_review_cycle.py')
    assert path.exists()
