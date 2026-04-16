from pathlib import Path


def test_overview_template_mentions_global_filled_reconciliation_banner():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert '未對齊成交提醒' in text
    assert '資料同步完成，但仍有未對齊成交' in text
