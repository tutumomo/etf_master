from pathlib import Path


def test_readme_mentions_agent_summary_bridge():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/README.md')
    text = path.read_text(encoding='utf-8')
    assert 'agent_summary.json' in text
