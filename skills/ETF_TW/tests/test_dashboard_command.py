from pathlib import Path


def test_etf_tw_includes_dashboard_command():
    path = Path('/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/etf_tw.py')
    text = path.read_text(encoding='utf-8')
    assert 'cmd_dashboard' in text
    assert 'sub.add_parser("dashboard"' in text
    assert 'if args.command == "dashboard"' in text
