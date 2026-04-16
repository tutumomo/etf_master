from pathlib import Path


def test_overview_template_contains_review_status_and_actions():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'markAIDecisionReviewed()' in text
    assert 'markAIDecisionSuperseded()' in text
    assert "ai_decision_response.get('review', {}).get('status')" in text


def test_dashboard_app_contains_review_update_route():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert '/api/ai-decision/review' in text
