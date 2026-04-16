from pathlib import Path


def test_overview_template_shows_decision_memory_context_summary():
    text = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html').read_text(encoding='utf-8')
    assert '最近記憶回饋' in text
    assert 'recent_review_count' in text
    assert 'recent_outcome_count' in text
    assert 'recent_reflection_count' in text
