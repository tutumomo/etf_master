from pathlib import Path


def test_dashboard_generate_route_mentions_auto_quality_refresh():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert '/api/ai-decision/generate' in text
    assert 'auto_refresh_quality_state' in text
