from pathlib import Path


def test_base_template_contains_fintech_visual_tokens():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/base.html')
    text = path.read_text(encoding='utf-8')
    assert '--panel' in text
    assert '--good' in text
    assert 'dashboard-shell' in text
    assert 'sidebar' in text
    assert 'data-theme="light"' in text
    assert 'applyDashboardTheme' in text


def test_overview_template_has_explicit_trading_mode_feedback():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/dashboard/templates/overview.html')
    text = path.read_text(encoding='utf-8')
    assert 'id="trading_mode_label"' in text
    assert 'id="btn_mode_live"' in text
    assert 'id="btn_mode_paper"' in text
    assert '切換中 → ${targetLabel}' in text
    assert '已按下切換至 ${targetLabel}' in text
