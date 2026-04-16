from pathlib import Path

# Relative to skills/ETF_TW/tests
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

SCRIPTS = [
    SCRIPTS_DIR / "sync_strategy_link.py",
    SCRIPTS_DIR / "sync_paper_state.py",
    SCRIPTS_DIR / "sync_agent_summary.py",
    SCRIPTS_DIR / "sync_market_cache.py",
    SCRIPTS_DIR / "sync_ohlcv_history.py",
    SCRIPTS_DIR / "generate_intraday_tape_context.py",
    SCRIPTS_DIR / "generate_taiwan_market_context.py",
    SCRIPTS_DIR / "generate_market_event_context.py",
    SCRIPTS_DIR / "check_major_event_trigger.py",
    SCRIPTS_DIR / "generate_watchlist_summary.py",
    SCRIPTS_DIR / "run_auto_decision_scan.py",
    SCRIPTS_DIR / "review_auto_decisions.py",
    SCRIPTS_DIR / "verify_alignment.py",
    SCRIPTS_DIR / "verify_decision_engine_stability.py",
    SCRIPTS_DIR / "update_experiment_decisions.py",
    SCRIPTS_DIR / "update_decision_outcomes.py",
    SCRIPTS_DIR / "score_decision_quality.py",
    SCRIPTS_DIR / "build_regime_bucket_stats.py",
    SCRIPTS_DIR / "update_context_weights.py",
]

FORBIDDEN_PATTERNS = [
    'ROOT / "state"',
    "ROOT / 'state'",
    'ETF_TW_ROOT / "state"',
    'STATE_DIR = ETF_TW_ROOT / "state"',
    '/skills/ETF_TW/state', # General check for hardcoded state path
]


def test_state_writers_do_not_hardcode_root_state_paths():
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in text, f"{path.name} still contains forbidden root-state pattern: {pattern}"


def test_state_writers_use_context_state_dir():
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        assert "context.get_state_dir()" in text or "STATE = context.get_state_dir()" in text or "STATE_DIR = context.get_state_dir()" in text, \
            f"{path.name} should use context.get_state_dir()"
