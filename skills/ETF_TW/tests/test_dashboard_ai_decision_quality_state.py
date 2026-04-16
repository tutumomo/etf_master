from pathlib import Path


def test_overview_template_mentions_ai_decision_quality_state():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'AI Quality State' in text
    assert "ai_decision_quality.get('confidence_bias')" in text
    assert "ai_decision_quality.get('quality_summary')" in text


def test_dashboard_app_loads_ai_decision_quality_state():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert 'ai_decision_quality.json' in text
