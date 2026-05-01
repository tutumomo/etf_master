from pathlib import Path
import importlib.util
import tempfile

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/run_auto_decision_scan.py")
spec = importlib.util.spec_from_file_location("run_auto_decision_scan", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _base_inputs():
    watchlist = {
        "items": [
            {"symbol": "00939", "group": "smart_beta"},
            {"symbol": "00720B", "group": "defensive"},
        ]
    }
    market_cache = {
        "quotes": {
            "00939": {"current_price": 16.8},
            "00720B": {"current_price": 32.7},
        }
    }
    portfolio = {"holdings": []}
    event_context = {"global_risk_level": "elevated", "geo_political_risk": "unknown"}
    tape_context = {"watchlist_signals": []}
    return watchlist, market_cache, portfolio, event_context, tape_context


def test_high_volatility_warning_overlay_prefers_defensive_candidate():
    watchlist, market_cache, portfolio, event_context, tape_context = _base_inputs()

    with tempfile.TemporaryDirectory() as td:
        module.STATE = Path(td)
        result = module.decide_action(
            strategy={"base_strategy": "防守保守", "scenario_overlay": "高波動警戒"},
            watchlist=watchlist,
            market_cache=market_cache,
            portfolio=portfolio,
            market_context={"risk_temperature": "elevated", "market_regime": "cautious"},
            event_context=event_context,
            tape_context=tape_context,
        )

    assert result["candidate"]["symbol"] == "00720B"
    assert result["candidate"]["group"] == "defensive"


def test_observation_mode_does_not_create_preview_candidate():
    watchlist, market_cache, portfolio, event_context, tape_context = _base_inputs()

    with tempfile.TemporaryDirectory() as td:
        module.STATE = Path(td)
        result = module.decide_action(
            strategy={"base_strategy": "觀察模式", "scenario_overlay": "無"},
            watchlist=watchlist,
            market_cache=market_cache,
            portfolio=portfolio,
            market_context={"risk_temperature": "normal", "market_regime": "balanced"},
            event_context=event_context,
            tape_context=tape_context,
        )

    assert result["action"] == "hold"
    assert result["candidate"] is None
    assert result["advisory_candidate"]["symbol"] == "00720B"
    assert "觀察模式" in result["summary"]


def test_hold_result_still_exposes_advisory_candidate():
    watchlist, market_cache, portfolio, event_context, tape_context = _base_inputs()

    with tempfile.TemporaryDirectory() as td:
        module.STATE = Path(td)
        result = module.decide_action(
            strategy={"base_strategy": "核心累積", "scenario_overlay": "無"},
            watchlist=watchlist,
            market_cache=market_cache,
            portfolio=portfolio,
            market_context={"risk_temperature": "elevated", "market_regime": "balanced"},
            event_context=event_context,
            tape_context=tape_context,
        )

    assert result["action"] == "hold"
    assert result["candidate"] is None
    assert result["advisory_candidate"]["symbol"] in {"00939", "00720B"}
    assert result["best_buy_candidate"]["symbol"] in {"00939", "00720B"}


def test_advisory_candidate_prefers_strategy_aligned_candidate():
    watchlist = {
        "items": [
            {"symbol": "00940", "group": "income"},
            {"symbol": "006208", "group": "core"},
        ]
    }
    market_cache = {
        "quotes": {
            "00940": {"current_price": 10.3},
            "006208": {"current_price": 209.7},
        }
    }
    portfolio = {"holdings": [{"symbol": "00940", "quantity": 400}]}

    with tempfile.TemporaryDirectory() as td:
        module.STATE = Path(td)
        result = module.decide_action(
            strategy={"base_strategy": "核心累積", "scenario_overlay": "無"},
            watchlist=watchlist,
            market_cache=market_cache,
            portfolio=portfolio,
            market_context={"risk_temperature": "elevated", "market_regime": "balanced"},
            event_context={"global_risk_level": "moderate"},
            tape_context={"watchlist_signals": []},
        )

    assert result["advisory_candidate"]["symbol"] == "006208"
    assert result["advisory_candidate"]["strategy_aligned"] is True
