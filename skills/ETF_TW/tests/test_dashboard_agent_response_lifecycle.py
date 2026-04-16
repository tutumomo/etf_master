from pathlib import Path


def test_overview_template_shows_agent_source_and_review_status():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert "ai_decision_response.get('source')" in text
    assert "ai_decision_response.get('review', {}).get('status')" in text
    assert "ai_decision_response.get('agent', {}).get('name')" in text
