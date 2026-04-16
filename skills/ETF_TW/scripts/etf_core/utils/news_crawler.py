"""
ETF_TW Pro - 情報爬蟲模組
掃描財經新聞、社群情緒、總經數據
"""
"""沙盒 DNS 修復"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict
import feedparser

def fetch_yahoo_finance_news(keyword: str = "台股", limit: int = 10) -> List[Dict]:
    """
    抓取 Yahoo 奇摩財經新聞
    """
    news_list = []
    try:
        # Yahoo 財經 RSS
        url = "https://tw.news.yahoo.com/rss"
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:limit]:
            title = entry.title
            link = entry.link
            published = entry.published if hasattr(entry, 'published') else datetime.now().isoformat()
            
            # 簡單的情緒評分 (後續會用 AI 優化)
            sentiment = 0  # 中性
            
            news_list.append({
                'title': title,
                'content': '',
                'sentiment_score': sentiment,
                'source': 'Yahoo 財經',
                'published_at': published,
                'link': link
            })
            
    except Exception as e:
        print(f"❌ 抓取 Yahoo 財經新聞失敗：{e}")
    
    return news_list

def fetch_ptt_stock_board(limit: int = 10) -> List[Dict]:
    """
    抓取 PTT 股票版 熱門文章
    """
    news_list = []
    try:
        url = "https://www.ptt.cc/bbs/Stock/index.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('data', {}).get('articles', [])[:limit]
            
            for article in articles:
                news_list.append({
                    'title': f"[PTT Stock] {article.get('title', '')}",
                    'content': '',
                    'sentiment_score': 0,
                    'source': 'PTT 股票版',
                    'published_at': datetime.fromtimestamp(article.get('create_time', 0)).isoformat(),
                    'link': f"https://www.ptt.cc/bbs/Stock/{article.get('link', '')}"
                })
                
    except Exception as e:
        print(f"❌ 抓取 PTT 股票版失敗：{e}")
    
    return news_list

def fetch_cnbc_news(limit: int = 10) -> List[Dict]:
    """
    抓取 CNBC 財經新聞 (英文)
    """
    news_list = []
    try:
        url = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:limit]:
            news_list.append({
                'title': f"[CNBC] {entry.title}",
                'content': '',
                'sentiment_score': 0,
                'source': 'CNBC',
                'published_at': entry.published if hasattr(entry, 'published') else datetime.now().isoformat(),
                'link': entry.link
            })
            
    except Exception as e:
        print(f"❌ 抓取 CNBC 新聞失敗：{e}")
    
    return news_list

def get_daily_news_summary(keyword: str = "台股") -> List[Dict]:
    """
    取得每日新聞摘要
    整合多個來源
    """
    all_news = []
    
    # 抓取各來源
    yahoo_news = fetch_yahoo_finance_news(keyword, limit=5)
    ptt_news = fetch_ptt_stock_board(limit=5)
    cnbc_news = fetch_cnbc_news(limit=5)
    
    all_news = yahoo_news + ptt_news + cnbc_news
    
    # 依時間排序
    all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    return all_news[:15]

def analyze_sentiment(text: str) -> float:
    """
    分析文字情緒 (簡易版，後續會用 AI 優化)
    回傳值：-1 (極度利空) 到 1 (極度利多)
    """
    positive_words = ['上漲', '利多', '成長', '獲利', '突破', '創高', '看好']
    negative_words = ['下跌', '利空', '衰退', '虧損', '跌破', '低點', '看壞']
    
    score = 0
    total = len(positive_words) + len(negative_words)
    
    for word in positive_words:
        if word in text:
            score += 1
    for word in negative_words:
        if word in text:
            score -= 1
    
    return score / total if total > 0 else 0

if __name__ == "__main__":
    # 測試情報爬蟲
    print("📰 測試情報爬蟲模組")
    
    # 抓取每日新聞摘要
    news = get_daily_news_summary()
    
    print(f"\n=== 今日新聞摘要 ({len(news)} 則) ===\n")
    for i, n in enumerate(news, 1):
        print(f"{i}. [{n['source']}] {n['title']}")
        print(f"   時間：{n['published_at']}")
        print(f"   連結：{n['link']}")
        print()
    
    print("\n✅ 情報爬蟲測試完成")
