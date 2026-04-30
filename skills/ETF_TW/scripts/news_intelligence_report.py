#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from scripts.etf_core import context
    from scripts.sync_news_via_opencli import _tag_article
except ImportError:
    from etf_core import context
    from sync_news_via_opencli import _tag_article

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = context.get_state_dir()
OUTPUT_NAME = "news_intelligence_report.json"
STALE_HOURS = 24
TW_TZ = ZoneInfo("Asia/Taipei")


def safe_load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default or {}


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=TW_TZ)
        return ts
    except ValueError:
        return None


def age_hours(value: str | None, now: datetime | None = None) -> float | None:
    ts = parse_ts(value)
    if not ts:
        return None
    now_value = now or datetime.now(tz=ts.tzinfo or timezone.utc)
    if ts.tzinfo and now_value.tzinfo is None:
        now_value = now_value.replace(tzinfo=ts.tzinfo)
    if now_value.tzinfo and ts.tzinfo is None:
        ts = ts.replace(tzinfo=now_value.tzinfo)
    return (now_value - ts).total_seconds() / 3600


def is_fresh_timestamp(value: str | None, now: datetime | None = None) -> bool:
    age = age_hours(value, now=now)
    return age is not None and 0 <= age <= STALE_HOURS


def normalize_opencli_articles(payload: dict) -> list[dict]:
    return [
        _tag_article({
            "title": item.get("title") or "",
            "href": item.get("href") or item.get("link") or "",
            "source": item.get("source") or payload.get("source") or "opencli",
        })
        for item in payload.get("articles", [])
        if item.get("title")
    ]


def normalize_headline_articles(payload: dict) -> list[dict]:
    articles = []
    for item in payload.get("headlines", []):
        title = item.get("title") if isinstance(item, dict) else str(item)
        if title:
            articles.append(_tag_article({
                "title": title,
                "href": item.get("link", "") if isinstance(item, dict) else "",
                "source": item.get("source", "headlines") if isinstance(item, dict) else "headlines",
            }))
    return articles


def normalize_rss_entries(payload: dict) -> list[dict]:
    articles = []
    for item in payload.get("entries", []):
        title = item.get("title")
        if title:
            articles.append(_tag_article({
                "title": title,
                "href": item.get("link", ""),
                "source": item.get("source", "rss"),
            }))
    return articles


def dedupe_articles(articles: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for article in articles:
        title = " ".join(str(article.get("title") or "").split())
        if not title or title in seen:
            continue
        seen.add(title)
        article["title"] = title
        unique.append(article)
    return unique


def classify_signal_strength(risk_flagged: int, negative_sentiment: int, tagged: int) -> str:
    if risk_flagged >= 3 or negative_sentiment >= 2:
        return "high"
    if risk_flagged >= 1 or tagged >= 5:
        return "medium"
    if tagged > 0:
        return "low"
    return "none"


def build_news_intelligence_report(state_dir: Path = STATE_DIR, now: datetime | None = None) -> dict[str, Any]:
    opencli = safe_load_json(state_dir / "news_articles.json", {})
    headlines = safe_load_json(state_dir / "news_headlines.json", {})
    rss = safe_load_json(ROOT / "data" / "news.json", {})

    sources = [
        ("opencli", opencli.get("fetched_at"), normalize_opencli_articles(opencli)),
        ("headlines", headlines.get("updated_at"), normalize_headline_articles(headlines)),
        ("rss", rss.get("updated_at"), normalize_rss_entries(rss)),
    ]
    source_status = []
    fresh_articles = []
    for name, timestamp, rows in sources:
        source_age = age_hours(timestamp, now=now)
        fresh = is_fresh_timestamp(timestamp, now=now)
        source_status.append({
            "source": name,
            "timestamp": timestamp,
            "age_hours": round(source_age, 2) if source_age is not None else None,
            "fresh": fresh,
            "article_count": len(rows),
        })
        if fresh:
            fresh_articles.extend(rows)

    articles = dedupe_articles(fresh_articles)

    tagged_articles = [a for a in articles if a.get("tags")]
    risk_flagged = [a for a in articles if "risk" in (a.get("categories") or [])]
    etf_related = [a for a in articles if "etf" in (a.get("categories") or [])]
    negative = [a for a in articles if a.get("sentiment_bias") == "negative"]

    source_ages = [item["age_hours"] for item in source_status if item["age_hours"] is not None]
    freshest_age = min([age for age in source_ages if age is not None], default=None)

    warnings = []
    if not articles:
        warnings.append("news_articles_empty")
    if freshest_age is None:
        warnings.append("news_timestamp_missing")
    elif freshest_age > STALE_HOURS:
        warnings.append("news_stale_over_24h")

    signal_strength = classify_signal_strength(len(risk_flagged), len(negative), len(tagged_articles))
    ai_bridge_candidate = not warnings and signal_strength in {"medium", "high"}

    return {
        "ok": not warnings,
        "warnings": warnings,
        "total_articles": len(articles),
        "tagged_articles": len(tagged_articles),
        "risk_flagged": len(risk_flagged),
        "etf_related": len(etf_related),
        "negative_sentiment": len(negative),
        "signal_strength": signal_strength,
        "ai_bridge_candidate": ai_bridge_candidate,
        "freshest_age_hours": round(freshest_age, 2) if freshest_age is not None else None,
        "sources": source_status,
        "top_tagged_titles": [a["title"] for a in tagged_articles[:5]],
        "updated_at": (now or datetime.now()).isoformat(),
        "source": "news_intelligence_report",
    }


def refresh_news_intelligence_report(state_dir: Path = STATE_DIR, output_name: str = OUTPUT_NAME) -> dict:
    report = build_news_intelligence_report(state_dir)
    (state_dir / output_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def build_brief(report: dict) -> str:
    if not report:
        return "新聞情報：尚無報告。"
    return (
        "新聞情報："
        f"{report.get('signal_strength', 'none')} 訊號，"
        f"風險 {report.get('risk_flagged', 0)} 則，"
        f"ETF {report.get('etf_related', 0)} 則，"
        f"AI Bridge候選={'是' if report.get('ai_bridge_candidate') else '否'}。"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build ETF_TW news intelligence quality report.")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="State directory")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = refresh_news_intelligence_report(Path(args.state_dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(build_brief(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
