from pathlib import Path


def test_dashboard_app_wires_auto_reflection_after_review_and_outcome():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert 'auto_reflect_if_ready' in text
    assert '/api/ai-decision/review' in text
    assert '/api/ai-decision/outcome' in text
