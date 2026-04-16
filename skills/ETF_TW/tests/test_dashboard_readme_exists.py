from pathlib import Path


def test_dashboard_readme_includes_agent_summary_sync():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/README.md')
    text = path.read_text(encoding='utf-8')
    assert 'sync_agent_summary.py' in text
    assert 'agent_summary.json' in text
