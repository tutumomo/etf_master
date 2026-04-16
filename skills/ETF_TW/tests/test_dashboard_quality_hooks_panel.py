from pathlib import Path


def test_overview_template_shows_quality_hooks_summary():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'confidence_bias' in text
    assert 'quality_summary' in text
    assert "ai_decision_response.get('reasoning', {}).get('risk_context_summary')" in text
