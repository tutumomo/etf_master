from pathlib import Path


def test_overview_page_template_contains_strategy_controls_without_duplicate_badges():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert 'base_strategy' in text
    assert 'scenario_overlay' in text
    assert '套用策略' in text
    assert "策略：{{ strategy.get('base_strategy'" not in text
    assert "情境：{{ strategy.get('scenario_overlay'" not in text


def test_dashboard_page_contains_trading_mode_card():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert '交易模式' in text
