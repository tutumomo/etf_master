from pathlib import Path


def test_overview_template_groups_rule_engine_and_ai_bridge_controls():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert '規則引擎操作' in text
    assert 'AI Bridge 操作' in text
    assert '立即規則掃描' in text
    assert '生成 AI 建議' in text
