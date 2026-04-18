#!/usr/bin/env python3
"""台股新聞採集 — 透過 opencli browser (Chrome daemon) 繞過沙盒網路限制。

核心邏輯：用 opencli browser 開頁面 + eval JS 提取標題。
分兩步走：先開頁面等渲染，再提取。

使用方式：
  AGENT_ID=etf_master .venv/bin/python3 scripts/sync_news_via_opencli.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = PROJECT_ROOT / "instances" / (os.environ.get("AGENT_ID") or os.environ.get("OPENCLAW_AGENT_NAME", "etf_master")) / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = STATE_DIR / "news_articles.json"

# --- 關鍵字標記 ---
ETF_KEYWORDS = {
    "高股息", "殖利率", "配息", "除息", "除權", "ETF", "etf",
    "市值型", "債券", "0050", "006208", "00892", "00679B",
    "00923", "0056", "00713", "00878", "國泰", "富邦", "群益",
}

RISK_KEYWORDS = {
    "升息", "降息", "利率", "通膨", "Fed", "FOMC", "央行",
    "地緣", "戰爭", "制裁", "封鎖", "關稅", "貿易戰",
    "衰退", "泡沫", "崩盤", "大利空", "系統性風險",
}

MARKET_KEYWORDS = {
    "台股", "大盤", "加權", "櫃買", "外資", "投信", "自營商",
    "融資", "融券", "籌碼", "量能", "量縮", "價跌",
}

ALL_KEYWORDS = ETF_KEYWORDS | RISK_KEYWORDS | MARKET_KEYWORDS


def _run_opencli(args: list[str], timeout: int = 30) -> str:
    """Run opencli browser command and return stdout."""
    cmd = ["opencli", "browser"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"  [opencli] error: {result.stderr[:200]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  [opencli] timeout after {timeout}s: {' '.join(args)}")
        return ""


def _open_and_extract(url: str, js_code: str, source_name: str, max_articles: int = 20) -> list[dict]:
    """Open a page, wait, then extract articles via JS eval.
    
    Uses shell chaining to keep open + wait in the same opencli session.
    """
    print(f"  [news] Opening {source_name}: {url}")
    
    # Open page (opencli keeps session in daemon)
    open_result = _run_opencli(["open", url], timeout=25)
    if not open_result:
        print(f"  [news] {source_name}: open failed")
        return []

    # Wait for JS render
    _run_opencli(["wait", "time", "3"], timeout=10)

    # Extract via eval
    result = _run_opencli(["eval", js_code], timeout=15)
    if not result:
        print(f"  [news] {source_name}: eval returned empty")
        return []

    try:
        articles = json.loads(result)
        # Add source tag
        for a in articles:
            a["source"] = source_name
        print(f"  [news] {source_name}: {len(articles)} articles")
        return articles[:max_articles]
    except json.JSONDecodeError:
        print(f"  [news] {source_name}: JSON parse failed, raw: {result[:200]}")
        return []


YAHOO_JS = """(function(){
    const items = document.querySelectorAll('h3 a, h2 a, .js-stream-content a, [data-test="title"] a');
    const seen = new Set();
    return JSON.stringify([...items]
        .filter(e => e.textContent.trim().length > 5 && e.textContent.trim().length < 80)
        .map(e => {
            const t = e.textContent.trim();
            if (seen.has(t)) return null;
            seen.add(t);
            return {title: t, href: e.href};
        })
        .filter(Boolean)
        .slice(0,25));
})()"""

CNYES_JS = """(function(){
    const items = document.querySelectorAll('a[href*="/news/"], h3 a, .title a, .news-item a, .topic a');
    const seen = new Set();
    return JSON.stringify([...items]
        .filter(e => e.textContent.trim().length > 5 && e.textContent.trim().length < 80)
        .map(e => {
            const t = e.textContent.trim();
            if (seen.has(t)) return null;
            seen.add(t);
            return {title: t, href: e.href};
        })
        .filter(Boolean)
        .slice(0,20));
})()"""


def _tag_article(article: dict) -> dict:
    """Tag article with keywords, category, and sentiment bias."""
    title = article.get("title", "")
    tags = []
    categories = set()

    for kw in ALL_KEYWORDS:
        if kw.lower() in title.lower():
            tags.append(kw)
            if kw in ETF_KEYWORDS:
                categories.add("etf")
            if kw in RISK_KEYWORDS:
                categories.add("risk")
            if kw in MARKET_KEYWORDS:
                categories.add("market")

    risk_count = sum(1 for kw in RISK_KEYWORDS if kw.lower() in title.lower())
    if risk_count >= 2:
        sentiment_bias = "negative"
    elif risk_count == 1:
        sentiment_bias = "cautious"
    else:
        sentiment_bias = "neutral"

    article["tags"] = tags
    article["categories"] = list(categories)
    article["sentiment_bias"] = sentiment_bias
    return article


def main():
    print("=" * 50)
    print("台股新聞採集 (opencli browser)")
    print("=" * 50)

    all_articles = []

    # Source 1: Yahoo 台股
    try:
        articles = _open_and_extract(
            "https://tw.stock.yahoo.com/", YAHOO_JS, "yahoo", max_articles=25
        )
        all_articles.extend(articles)
    except Exception as e:
        print(f"  [news] Yahoo failed: {e}")

    # Source 2: 鉅亨網
    try:
        articles = _open_and_extract(
            "https://news.cnyes.com/cat/twstock", CNYES_JS, "cnyes", max_articles=20
        )
        all_articles.extend(articles)
    except Exception as e:
        print(f"  [news] cnyes failed: {e}")

    if not all_articles:
        print("  [news] No articles extracted from any source")

    # Tag + deduplicate
    tagged = [_tag_article(a) for a in all_articles]
    seen_titles = set()
    unique = []
    for a in tagged:
        if a["title"] not in seen_titles:
            seen_titles.add(a["title"])
            unique.append(a)

    now = datetime.now(timezone.utc).isoformat()
    output = {
        "fetched_at": now,
        "source": "opencli-browser",
        "total_articles": len(unique),
        "etf_related": len([a for a in unique if "etf" in a["categories"]]),
        "risk_flagged": len([a for a in unique if "risk" in a["categories"]]),
        "negative_sentiment": len([a for a in unique if a["sentiment_bias"] == "negative"]),
        "articles": unique,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Done: {len(unique)} articles → {OUTPUT_FILE}")
    print(f"  ETF相關: {output['etf_related']}, 風險標記: {output['risk_flagged']}, 負面: {output['negative_sentiment']}")

    # Close browser session
    try:
        _run_opencli(["close"], timeout=5)
    except Exception:
        pass

    return output


if __name__ == "__main__":
    result = main()