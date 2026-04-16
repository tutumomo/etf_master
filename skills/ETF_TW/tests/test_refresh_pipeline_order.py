from pathlib import Path

REFRESH_SCRIPT = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/refresh_monitoring_state.py")


def test_refresh_pipeline_contains_expected_core_order():
    text = REFRESH_SCRIPT.read_text(encoding="utf-8")

    expected_order = [
        '"sync_market_cache.py"',
        '"generate_market_event_context.py"',
        '"generate_taiwan_market_context.py"',
        '"check_major_event_trigger.py"',
        '"sync_portfolio_snapshot.py"',
        '"sync_ohlcv_history.py"',
        '"generate_intraday_tape_context.py"',
        '"sync_agent_summary.py"',
    ]

    positions = [text.index(token) for token in expected_order]
    assert positions == sorted(positions), "refresh pipeline core order has drifted"


def test_refresh_pipeline_keeps_summary_last():
    text = REFRESH_SCRIPT.read_text(encoding="utf-8")
    assert text.index('"sync_agent_summary.py"') > text.index('"generate_intraday_tape_context.py"')
    assert text.index('"sync_agent_summary.py"') > text.index('"sync_portfolio_snapshot.py"')


def test_refresh_pipeline_runs_market_context_before_event_trigger_check():
    text = REFRESH_SCRIPT.read_text(encoding="utf-8")
    assert text.index('"generate_taiwan_market_context.py"') < text.index('"check_major_event_trigger.py"')
