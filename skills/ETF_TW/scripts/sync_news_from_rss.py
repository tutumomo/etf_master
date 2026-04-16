import feedparser
import json
import os
from datetime import datetime

# RSS feeds to fetch
FEEDS = [
    "https://tw.news.yahoo.com/rss/finance",
    "https://news.cnyes.com/rss/headlines",
    "https://www.money-link.com.tw/rss/news_list.aspx?kind=1",
]

OUTPUT_PATH = os.path.expanduser("~/.hermes/profiles/etf_master/skills/ETF_TW/data/news.json")

def fetch_rss():
    all_entries = []
    for url in FEEDS:
        print(f"Fetching {url}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "source": url
                })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    
    # Sort by published date if possible
    # (Simplified for now)
    
    data = {
        "updated_at": datetime.now().isoformat(),
        "entries": all_entries[:50] # Top 50 entries
    }
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(all_entries)} entries to {OUTPUT_PATH}")

if __name__ == "__main__":
    fetch_rss()
