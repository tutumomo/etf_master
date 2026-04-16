from pathlib import Path


def test_overview_template_mentions_filled_reconciliation_section():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert 'Filled Reconciliation' in text or '成交對齊' in text
