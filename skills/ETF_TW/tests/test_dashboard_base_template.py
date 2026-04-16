from pathlib import Path


def test_base_template_contains_fintech_visual_tokens():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/base.html')
    text = path.read_text(encoding='utf-8')
    assert 'radial-gradient' in text
    assert '--panel' in text
    assert '--good' in text
