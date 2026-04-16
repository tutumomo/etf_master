"""
ETF_Master - Telegram 推送模組
Telegram 推送格式化輔助模組
"""
from datetime import datetime
from typing import Optional, List, Dict

def format_market_report(summary: Dict, holdings: List[Dict]) -> str:
    """
    格式化市場報告為 Telegram 訊息
    """
    lines = []
    lines.append("📊 *[ETF 盤前報告]*")
    lines.append(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("*市場狀態:*")
    
    for etf in summary.get('etf_summary', []):
        signal_icon = "🟢" if "超賣" in etf.get('signal', '') or "站上" in etf.get('signal', '') else "🔴"
        lines.append(f"{signal_icon} {etf['symbol']}: {etf['price']:.2f} ({etf['change_percent']:+.2f}%) - {etf.get('signal', '中性')}")
    
    lines.append("")
    lines.append("*持倉狀況:*")
    total_value = sum(h.get('value', 0) for h in holdings)
    total_profit = sum(h.get('profit_loss', 0) for h in holdings)
    
    for h in holdings:
        icon = "✅" if h.get('profit_loss', 0) > 0 else "❌"
        lines.append(f"{icon} {h['symbol']}: {h['quantity']}股 | 均價 {h['avg_cost']:.2f} | 現價 {h['current_price']:.2f} | 損益 {h['profit_loss']:+.0f} ({h['profit_loss_percent']:+.2f}%)")
    
    lines.append("")
    lines.append(f"*總持倉價值:* {total_value:,.0f}")
    lines.append(f"*總損益:* {total_profit:+,.0f}")
    
    return "\n".join(lines)

def format_trade_alert(symbol: str, action: str, price: float, quantity: int, reason: str) -> str:
    """
    格式化交易預警
    """
    icon = "🟢" if action == "BUY" else "🔴"
    action_text = "買進" if action == "BUY" else "賣出"
    
    lines = []
    lines.append(f"{icon} *[交易預警]*")
    lines.append(f"標的：{symbol}")
    lines.append(f"操作：{action_text}")
    lines.append(f"價格：{price:.2f}")
    lines.append(f"數量：{quantity} 股")
    lines.append(f"原因：{reason}")
    lines.append("")
    lines.append("_請主人確認是否執行：_")
    lines.append("✅ 確認執行  |  ❌ 取消")
    
    return "\n".join(lines)

def format_news_alert(title: str, source: str, sentiment: float, summary: str) -> str:
    """
    格式化新聞預警
    """
    sentiment_icon = "🟢" if sentiment > 0.3 else ("🔴" if sentiment < -0.3 else "⚪")
    sentiment_text = "利多" if sentiment > 0.3 else ("利空" if sentiment < -0.3 else "中性")
    
    lines = []
    lines.append(f"📰 *[{sentiment_text} 重大消息]*")
    lines.append(f"來源：{source}")
    lines.append(f"標題：{title}")
    lines.append("")
    lines.append(f"摘要：{summary[:200]}...")
    lines.append("")
    lines.append(f"*影響評估：* {sentiment_text}，建議關注相關標的。")
    
    return "\n".join(lines)

if __name__ == "__main__":
    # 測試推送格式
    print("測試 Telegram 推送格式")
    
    # 測試市場報告
    test_summary = {
        'etf_summary': [
            {'symbol': '0050.TW', 'price': 75.75, 'change_percent': -1.5, 'signal': 'RSI 超賣'},
            {'symbol': '006208.TW', 'price': 175.6, 'change_percent': 0.5, 'signal': '站上 MA20'}
        ]
    }
    test_holdings = [
        {'symbol': '0050.TW', 'quantity': 100, 'avg_cost': 75.0, 'current_price': 75.75, 'value': 7575, 'profit_loss': 75, 'profit_loss_percent': 1.0}
    ]
    
    print("\n=== 市場報告 ===")
    print(format_market_report(test_summary, test_holdings))
    
    print("\n=== 交易預警 ===")
    print(format_trade_alert('0050.TW', 'BUY', 75.75, 100, 'RSI 超賣，技術面反彈訊號'))
    
    print("\n=== 新聞預警 ===")
    print(format_news_alert('台積電法說會超預期', 'Yahoo 財經', 0.8, '台積電今日召開法說會，公布 Q3 營收與獲利均優於市場預期...'))
