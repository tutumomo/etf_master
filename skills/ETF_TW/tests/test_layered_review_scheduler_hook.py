from pathlib import Path


def test_scheduler_hook_script_exists():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/schedule_layered_reviews.py')
    assert path.exists()
