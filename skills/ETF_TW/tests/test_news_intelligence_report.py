from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, "/Users/tuchengshin/.hermes/profiles/etf_master/skills/ETF_TW/scripts")
import news_intelligence_report as module


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_news_intelligence_report_scores_risk_signal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _write(tmp_path / "state" / "news_articles.json", {
        "fetched_at": "2026-04-30T08:00:00+00:00",
        "source": "opencli-browser",
        "articles": [
            {"title": "Fed 升息 通膨 牽動台股 ETF", "source": "yahoo"},
            {"title": "0050 ETF 配息題材延燒", "source": "cnyes"},
        ],
    })

    report = module.build_news_intelligence_report(
        tmp_path / "state",
        now=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert report["ok"] is True
    assert report["total_articles"] == 2
    assert report["risk_flagged"] == 1
    assert report["etf_related"] == 2
    assert report["signal_strength"] == "medium"
    assert report["ai_bridge_candidate"] is True


def test_build_news_intelligence_report_warns_when_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)

    report = module.build_news_intelligence_report(tmp_path / "state")

    assert report["ok"] is False
    assert "news_articles_empty" in report["warnings"]
    assert report["signal_strength"] == "none"
    assert report["ai_bridge_candidate"] is False


def test_build_news_intelligence_report_warns_when_stale(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _write(tmp_path / "state" / "news_articles.json", {
        "fetched_at": "2026-04-29T00:00:00+00:00",
        "articles": [{"title": "台股 ETF 今日量縮", "source": "yahoo"}],
    })

    report = module.build_news_intelligence_report(
        tmp_path / "state",
        now=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert "news_stale_over_24h" in report["warnings"]
    assert report["ai_bridge_candidate"] is False


def test_build_news_intelligence_report_ignores_stale_source_when_rss_is_fresh(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _write(tmp_path / "state" / "news_articles.json", {
        "fetched_at": "2026-04-13T17:26:25+00:00",
        "articles": [{"title": "Fed 升息 通膨 牽動舊聞", "source": "opencli"}],
    })
    _write(tmp_path / "data" / "news.json", {
        "updated_at": "2026-04-30T23:00:00",
        "entries": [{"title": "0050 ETF 配息 今日更新", "source": "rss"}],
    })

    report = module.build_news_intelligence_report(
        tmp_path / "state",
        now=datetime(2026, 4, 30, 23, 30, tzinfo=module.TW_TZ),
    )

    assert report["ok"] is True
    assert report["total_articles"] == 1
    assert report["freshest_age_hours"] == 0.5
    assert report["top_tagged_titles"] == ["0050 ETF 配息 今日更新"]


def test_build_brief_mentions_ai_bridge_candidate():
    brief = module.build_brief({
        "signal_strength": "medium",
        "risk_flagged": 1,
        "etf_related": 2,
        "ai_bridge_candidate": True,
    })
    assert "medium 訊號" in brief
    assert "AI Bridge候選=是" in brief
