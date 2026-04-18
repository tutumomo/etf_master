#!/usr/bin/env python3
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

"""
sync_news_from_local.py — 在本機執行，抓台股新聞 RSS → 摘要 → 事件標籤

因沙盒無外網，此腳本由使用者在真實終端機執行：
  cd ~/.hermes/profiles/etf_master/skills/ETF_TW
  AGENT_ID=etf_master .venv/bin/python3 scripts/sync_news_from_local.py

資料來源：
1. 鉅亨網 RSS (tw_stock)
2. Yahoo 台灣財經 RSS

輸出：state/news_headlines.json
欄位：
- headlines: [{title, link, source, published, tags[], sentiment}]
- updated_at
- source

tags 由關鍵字比對產出（不依賴 LLM）：
- rate_decision: 利率/升息/降息/央行/FOMC
- geo_risk: 地緣/兩岸/戰爭/制裁/關稅
- earnings: 財報/營收/盈餘/EPS
- etf_related: ETF/配息/除息/殖利率
- market_sentiment: 暴跌/大漲/崩盤/創高/破底
- sector_tech: 半導體/晶片/AI/台積電
- sector_finance: 金融/銀行/壽險/金控
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'scripts'))

from etf_core.state_io import atomic_save_json
from etf_core import context

STATE = context.get_state_dir()
TW_TZ = ZoneInfo('Asia/Taipei')
NEWS_PATH = STATE / 'news_headlines.json'

# RSS feeds to try
RSS_FEEDS = [
    {
        'name': 'anue_stock',
        'url': 'https://news.cnyes.com/rss/cat/tw_stock',
        'type': 'rss',
    },
    {
        'name': 'anue_fund',
        'url': 'https://news.cnyes.com/rss/cat/fund',
        'type': 'rss',
    },
]

# Tag rules: (tag_name, keywords)
TAG_RULES = [
    ('rate_decision', ['利率', '升息', '降息', '央行', 'FOMC', 'Fed', '聯準會', '理監事', '貨幣政策', '殖利率曲線']),
    ('geo_risk', ['地緣', '兩岸', '戰爭', '制裁', '關稅', '貿易戰', '南中國海', '台海', '晶片法', '出口管制']),
    ('earnings', ['財報', '營收', '盈餘', 'EPS', '毛利率', '獲利', '虧損', '季報', '年報']),
    ('etf_related', ['ETF', '配息', '除息', '殖利率', '指數型', '0050', '006208', '00892', '00679B']),
    ('market_sentiment', ['暴跌', '大漲', '崩盤', '創高', '破底', '殺盤', '軋空', '恐慌', '樂觀', '樂觀看待']),
    ('sector_tech', ['半導體', '晶片', 'AI', '台積電', '聯發科', '鴻海', '輝達', 'NVIDIA', '封測', '矽智財']),
    ('sector_finance', ['金融', '銀行', '壽險', '金控', '放款', '利差', '壞帳', '資本適足率']),
]

# Sentiment keywords
BULLISH_WORDS = ['大漲', '創高', '看好', '樂觀', '反彈', '利多', '突破', '軋空', '資金流入']
BEARISH_WORDS = ['暴跌', '崩盤', '破底', '看淡', '悲觀', '利空', '跌破', '殺盤', '資金外流', '恐慌']


def _tag_headline(title: str) -> list[str]:
    """Apply keyword-based tagging."""
    tags = []
    for tag_name, keywords in TAG_RULES:
        if any(kw in title for kw in keywords):
            tags.append(tag_name)
    return tags


def _sentiment_headline(title: str) -> str:
    """Simple keyword sentiment: bullish/bearish/neutral."""
    bull = sum(1 for w in BULLISH_WORDS if w in title)
    bear = sum(1 for w in BEARISH_WORDS if w in title)
    if bull > bear:
        return 'bullish'
    elif bear > bull:
        return 'bearish'
    return 'neutral'


def _parse_rss_feed(url: str, source_name: str) -> list[dict]:
    """Fetch and parse an RSS feed."""
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'ETF_TW/1.0'})
        if r.status_code != 200:
            print(f"  [{source_name}] HTTP {r.status_code}")
            return []

        root = ElementTree.fromstring(r.text)
        items = []

        # Handle both RSS 2.0 and Atom
        ns = {}
        if root.tag.endswith('}feed') or root.tag == 'feed':
            # Atom
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            if not entries:
                entries = root.findall('.//entry')
            for entry in entries:
                title_el = entry.find('{http://www.w3.org/2005/Atom}title') or entry.find('title')
                link_el = entry.find('{http://www.w3.org/2005/Atom}link') or entry.find('link')
                pub_el = entry.find('{http://www.w3.org/2005/Atom}published') or entry.find('published') or entry.find('{http://www.w3.org/2005/Atom}updated') or entry.find('updated')

                title = title_el.text if title_el is not None and title_el.text else ''
                link = link_el.get('href', '') if link_el is not None else ''
                published = pub_el.text if pub_el is not None else ''

                if title:
                    items.append({
                        'title': title.strip(),
                        'link': link,
                        'source': source_name,
                        'published': published,
                    })
        else:
            # RSS 2.0
            for item in root.iter('item'):
                title_el = item.find('title')
                link_el = item.find('link')
                pub_el = item.find('pubDate')

                title = title_el.text if title_el is not None and title_el.text else ''
                link = link_el.text if link_el is not None and link_el.text else ''
                published = pub_el.text if pub_el is not None else ''

                if title:
                    items.append({
                        'title': title.strip(),
                        'link': link,
                        'source': source_name,
                        'published': published,
                    })

        print(f"  [{source_name}] Found {len(items)} items")
        return items

    except Exception as e:
        print(f"  [{source_name}] FAIL: {e}")
        return []


def sync_news() -> dict:
    """Main sync function."""
    now = datetime.now(TW_TZ)
    all_raw = []

    for feed in RSS_FEEDS:
        raw = _parse_rss_feed(feed['url'], feed['name'])
        all_raw.extend(raw)

    # Deduplicate by title (first 30 chars)
    seen = set()
    headlines = []
    for raw in all_raw:
        key = raw['title'][:30]
        if key in seen:
            continue
        seen.add(key)

        tags = _tag_headline(raw['title'])
        sentiment = _sentiment_headline(raw['title'])

        headlines.append({
            'title': raw['title'],
            'link': raw.get('link', ''),
            'source': raw.get('source', ''),
            'published': raw.get('published', ''),
            'tags': tags,
            'sentiment': sentiment,
        })

    # Sort: tagged first, then by published date
    headlines.sort(key=lambda h: (len(h['tags']) * -1, h.get('published', '')), reverse=False)

    # Aggregate stats
    tag_counts = {}
    sentiment_counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    for h in headlines:
        sentiment_counts[h['sentiment']] = sentiment_counts.get(h['sentiment'], 0) + 1
        for t in h['tags']:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    payload = {
        'headlines': headlines[:50],  # Top 50
        'total_fetched': len(all_raw),
        'total_unique': len(headlines),
        'tag_counts': tag_counts,
        'sentiment_counts': sentiment_counts,
        'updated_at': now.isoformat(),
        'source': 'rss_keyword_v1',
    }

    atomic_save_json(NEWS_PATH, payload)
    print(f"\nNEWS_OK: {len(headlines)} unique headlines, tags={tag_counts}, sentiment={sentiment_counts}")
    return payload


if __name__ == '__main__':
    sync_news()