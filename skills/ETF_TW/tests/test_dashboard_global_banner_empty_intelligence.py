from pathlib import Path


def test_overview_template_mentions_empty_intelligence_banner_text():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert '技術指標資料尚未建立' in text
    assert '資料同步完成，但技術指標資料尚未建立' in text
