from pathlib import Path
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import portfolio_risk_report as module


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _history(prices: list[float]) -> list[dict]:
    return [{"t": f"2026-04-{idx + 1:02d}T13:30:00+08:00", "c": price} for idx, price in enumerate(prices)]


def test_max_drawdown_and_volatility_from_prices():
    prices = [100, 110, 90, 95]
    assert module.max_drawdown(prices) == 0.181818
    assert module.annualized_volatility(module.returns_from_prices(prices)) is not None


def test_build_portfolio_risk_report_blocks_buy_on_large_drawdown(tmp_path: Path):
    _write(tmp_path / "positions.json", {"positions": [{"symbol": "0050", "quantity": 1000}]})
    _write(tmp_path / "market_intelligence.json", {
        "intelligence": {
            "0050": {"history_30d": _history([100, 120, 90, 88])}
        }
    })
    _write(tmp_path / "position_peak_tracker.json", {})

    report = module.build_portfolio_risk_report(tmp_path)

    assert report["block_buy"] is True
    assert "max_drawdown_block" in report["blockers"]
    assert report["portfolio"]["max_drawdown"] >= 0.2


def test_build_portfolio_risk_report_flags_high_correlation(tmp_path: Path):
    _write(tmp_path / "positions.json", {"positions": [
        {"symbol": "0050", "quantity": 1000},
        {"symbol": "006208", "quantity": 1000},
    ]})
    _write(tmp_path / "market_intelligence.json", {
        "intelligence": {
            "0050": {"history_30d": _history([100, 101, 102, 103, 104])},
            "006208": {"history_30d": _history([200, 202, 204, 206, 208])},
        }
    })
    _write(tmp_path / "position_peak_tracker.json", {})

    report = module.build_portfolio_risk_report(tmp_path)

    assert report["block_buy"] is False
    assert "high_correlation_warning" in report["warnings"]
    assert report["correlation"]["high_correlation_pairs"][0]["symbols"] == ["0050", "006208"]


def test_build_portfolio_risk_report_detects_trailing_stop_mismatch(tmp_path: Path):
    _write(tmp_path / "positions.json", {"positions": [{"symbol": "0050", "quantity": 1000}]})
    _write(tmp_path / "market_intelligence.json", {
        "intelligence": {"0050": {"history_30d": _history([100, 101, 102, 103])}}
    })
    _write(tmp_path / "position_peak_tracker.json", {
        "0050": {"peak_close": 120.0, "trailing_pct": 0.12, "stop_price": 100.0}
    })

    report = module.build_portfolio_risk_report(tmp_path)

    assert "trailing_stop_alignment_mismatch" in report["warnings"]
    assert report["trailing_alignment"]["mismatches"][0]["expected_stop"] == 105.6


def test_build_brief_reports_block_state():
    brief = module.build_brief({
        "block_buy": True,
        "warnings": [],
        "portfolio": {"max_drawdown": 0.21, "volatility_annualized": 0.18},
    })
    assert "阻擋買入" in brief
    assert "21.0%" in brief
