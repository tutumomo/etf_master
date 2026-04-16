from pathlib import Path


def test_overview_template_has_distinct_rule_engine_and_ai_bridge_sections():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert 'rule-engine-panel' in text
    assert 'ai-bridge-panel' in text
