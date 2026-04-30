from pathlib import Path
import importlib.util

MODULE_PATH = Path("/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts/sync_agent_summary.py")
spec = importlib.util.spec_from_file_location("sync_agent_summary", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_strategy_header():
    assert module.build_strategy_header({'base_strategy':'平衡配置','scenario_overlay':'無'}) == '[目前投資策略:平衡配置, 情境覆蓋:無]'


def test_mode_brief_format_example():
    payload = {
        "effective_mode": "live-ready",
        "data_source": "live_broker",
    }
    mode_label = (payload.get("effective_mode") or "unknown").upper()
    data_source = payload.get("data_source") or "unknown"
    assert f"目前模式 {mode_label}，資料來源 {data_source}。" == "目前模式 LIVE-READY，資料來源 live_broker。"


def test_reconciliation_brief_mentions_unreconciled_symbols():
    brief = module.build_reconciliation_brief({
        "ok": False,
        "unreconciled_count": 1,
        "unreconciled_symbols": ["006208"],
    })
    assert "1 檔尚未對齊 positions" in brief
    assert "006208" in brief


def test_reconciliation_brief_ok_state():
    assert module.build_reconciliation_brief({
        "ok": True,
        "unreconciled_count": 0,
        "unreconciled_symbols": [],
    }) == "成交對帳狀態：已對齊 positions。"


def test_decision_quality_brief_uses_chain_breakdown():
    brief = module.build_decision_quality_brief({
        "chain_breakdown": {
            "tier1_consensus": {"total": 5, "win_rate": 0.8},
            "rule_engine": {"total": 10, "win_rate": 0.6},
            "ai_bridge": {"total": 8, "win_rate": 0.5},
        }
    })
    assert "Tier1共識勝率 80.0%" in brief
    assert "規則 60.0%" in brief
    assert "AI 50.0%" in brief


def test_data_quality_brief_mentions_missing_quotes():
    brief = module.build_data_quality_brief({
        "ok": False,
        "issues": ["missing_required_quotes"],
        "warnings": ["positions_snapshot_symbol_drift"],
        "missing_quote_symbols": ["006208"],
    })
    assert "issues 1" in brief
    assert "warnings 1" in brief
    assert "006208" in brief


def test_data_quality_brief_ok_state():
    brief = module.build_data_quality_brief({
        "ok": True,
        "issues": [],
        "warnings": [],
        "freshness": {"market_cache_age_minutes": 12.4},
    })
    assert brief == "資料品質：正常，market_cache 約 12 分鐘前更新。"


def test_portfolio_risk_brief_reports_block_state():
    brief = module.build_portfolio_risk_brief({
        "block_buy": True,
        "warnings": [],
        "portfolio": {"max_drawdown": 0.21, "volatility_annualized": 0.18},
    })
    assert "阻擋買入" in brief
    assert "最大回撤 21.0%" in brief


def test_portfolio_risk_brief_reports_warning_count():
    brief = module.build_portfolio_risk_brief({
        "block_buy": False,
        "warnings": ["high_correlation_warning"],
        "portfolio": {"max_drawdown": 0.05, "volatility_annualized": 0.2},
    })
    assert "可買入" in brief
    assert "warnings 1" in brief


def test_news_intelligence_brief_mentions_ai_bridge_candidate():
    brief = module.build_news_intelligence_brief({
        "signal_strength": "medium",
        "risk_flagged": 1,
        "etf_related": 2,
        "ai_bridge_candidate": True,
    })
    assert "medium 訊號" in brief
    assert "AI Bridge候選=是" in brief
