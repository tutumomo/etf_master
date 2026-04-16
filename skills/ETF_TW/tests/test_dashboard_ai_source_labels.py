from pathlib import Path


def test_overview_template_contains_source_and_freshness_labels():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert '來源：Rule Engine' in text
    assert '來源：AI Bridge' in text
    assert "ai_decision_response.get('generated_at')" in text
    assert "auto_trade_state.get('updated_at')" in text
