from pathlib import Path


def test_overview_template_contains_ai_bridge_action_buttons():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'refreshAIDecisionBackground()' in text
    assert 'generateAIDecision()' in text
    assert 'rerunAIDecisionPipeline()' in text


def test_dashboard_app_contains_ai_bridge_action_routes():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/app.py').read_text(encoding='utf-8')
    assert '/api/ai-decision/refresh-background' in text
    assert '/api/ai-decision/generate' in text
    assert '/api/ai-decision/rerun' in text
