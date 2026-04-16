from pathlib import Path


def test_overview_template_contains_outcome_actions():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'recordAIOutcomeTracked()' in text
    assert 'recordAIOutcomeReviewed()' in text


def test_dashboard_app_contains_outcome_route():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert '/api/ai-decision/outcome' in text
