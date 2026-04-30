import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import etf_tw as module


def test_build_status_lines_includes_mode_account_and_data_quality():
    lines = module.build_status_lines(
        mode={"effective_mode": "paper", "data_source": "paper_ledger"},
        account={"cash": 1000, "total_equity": 5000, "source": "paper_ledger"},
        positions={"positions": [{"symbol": "006208"}]},
        summary={"filled_reconciliation": {"ok": True}},
        data_quality={"ok": True, "issues": [], "warnings": []},
        portfolio_risk={
            "block_buy": False,
            "warnings": [],
            "portfolio": {"max_drawdown": 0.05, "volatility_annualized": 0.18},
        },
        news_intelligence={
            "signal_strength": "low",
            "risk_flagged": 0,
            "etf_related": 1,
            "ai_bridge_candidate": False,
        },
    )

    text = "\n".join(lines)
    assert "目前模式: PAPER" in text
    assert "資料來源: paper_ledger" in text
    assert "現金: NT$ 1,000" in text
    assert "持倉: 1 檔" in text
    assert "成交對帳: OK" in text
    assert "資料品質：正常" in text
    assert "組合風控：可買入" in text
    assert "新聞情報：low 訊號" in text


def test_build_status_lines_surfaces_data_quality_missing_quotes():
    lines = module.build_status_lines(
        mode={"effective_mode": "paper"},
        account={},
        positions={"positions": []},
        summary={},
        data_quality={
            "ok": False,
            "issues": ["missing_required_quotes"],
            "warnings": [],
            "missing_quote_symbols": ["006208"],
        },
        portfolio_risk={},
        news_intelligence={},
    )

    assert any("缺報價: 006208" in line for line in lines)
