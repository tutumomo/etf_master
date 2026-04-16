from pathlib import Path


def test_overview_template_contains_ai_decision_bridge_panel_bindings():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'AI Decision Bridge' in text
    assert "ai_decision_request.get('request_id')" in text
    assert "ai_decision_response.get('decision', {}).get('summary')" in text
    assert "ai_decision_response.get('stale')" in text
