"""
ETF_TW Pro - 資料庫模組
負責 SQLite 資料庫的初始化與操作
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = "db/etf_tw.db"

def init_db():
    """初始化資料庫，建立必要的資料表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 持倉表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etf_code TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(etf_code)
        )
    ''')
    
    # 交易紀錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etf_code TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('BUY', 'SELL')),
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            fee REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 情報表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            sentiment_score REAL DEFAULT 0,
            source TEXT,
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 模擬盤資金表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            cash REAL NOT NULL DEFAULT 1000000,
            initial_cash REAL NOT NULL DEFAULT 1000000,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 初始化預設模擬資金
    cursor.execute('''
        INSERT OR IGNORE INTO portfolio (user_id, cash, initial_cash)
        VALUES ('default', 1000000, 1000000)
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 資料庫已初始化：{DB_PATH}")

def add_holding(etf_code: str, quantity: int, avg_cost: float):
    """新增或更新持倉"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO holdings (etf_code, quantity, avg_cost)
        VALUES (?, ?, ?)
        ON CONFLICT(etf_code) DO UPDATE SET
            quantity = quantity + excluded.quantity,
            avg_cost = (avg_cost * quantity + excluded.avg_cost * excluded.quantity) / (quantity + excluded.quantity),
            last_updated = CURRENT_TIMESTAMP
        WHERE etf_code = excluded.etf_code
    ''', (etf_code, quantity, avg_cost))
    conn.commit()
    conn.close()

def get_holdings() -> List[Dict]:
    """取得所有持倉"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM holdings WHERE quantity > 0')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_transaction(etf_code: str, type_: str, price: float, quantity: int, fee: float = 0):
    """新增交易紀錄"""
    total_amount = price * quantity + fee if type_ == 'BUY' else price * quantity - fee
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (etf_code, type, price, quantity, fee, total_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (etf_code, type_, price, quantity, fee, total_amount))
    conn.commit()
    conn.close()

def get_transactions(limit: int = 50) -> List[Dict]:
    """取得交易紀錄"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_news(title: str, content: str, sentiment_score: float, source: str, published_at: Optional[datetime] = None):
    """新增情報"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO news (title, content, sentiment_score, source, published_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, content, sentiment_score, source, published_at))
    conn.commit()
    conn.close()

def get_news(limit: int = 20) -> List[Dict]:
    """取得情報"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_portfolio() -> Dict:
    """取得模擬盤資金狀況"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM portfolio WHERE user_id = ?', ('default',))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {'cash': 1000000, 'initial_cash': 1000000}

def update_portfolio_cash(cash: float):
    """更新模擬盤現金"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE portfolio SET cash = ?, last_updated = CURRENT_TIMESTAMP
        WHERE user_id = 'default'
    ''', (cash,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # 測試資料庫初始化
    init_db()
    print("✅ 資料庫測試完成")
