"""
Database utilities for CryptoLens
"""

import sqlite3
import json
import time
from typing import Optional, List, Dict, Any

DB_PATH = "crypto_data.db"

def init_db(db_path: str = DB_PATH):
    """Initialize database tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # OHLCV table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            open_time   INTEGER NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      REAL,
            close_time  INTEGER,
            UNIQUE(symbol, open_time)
        )
    """)

    # Order book snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_book_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            timestamp   INTEGER NOT NULL,
            bids        TEXT,   -- JSON string
            asks        TEXT    -- JSON string
        )
    """)

    # Live trades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT,
            price       REAL,
            quantity    REAL,
            trade_time  INTEGER,
            is_buyer_mm INTEGER
        )
    """)

    # Live book ticker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_book_ticker (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT,
            timestamp   INTEGER,
            best_bid    REAL,
            best_ask    REAL,
            bid_qty     REAL,
            ask_qty     REAL
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {db_path}")

def get_db_stats(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Get database statistics."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all symbols in ohlcv
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv")
        symbols = [row[0] for row in cursor.fetchall()]
        
        stats = {}
        for symbol in symbols:
            cursor.execute(
                "SELECT COUNT(*) FROM ohlcv WHERE symbol=?", 
                (symbol,)
            )
            stats[symbol] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except:
        return {}

def save_ohlcv(df, symbol, db_path: str = DB_PATH):
    """Save OHLCV data to database."""
    conn = sqlite3.connect(db_path)
    
    # Use INSERT OR IGNORE to avoid duplicates
    for _, row in df.iterrows():
        try:
            conn.execute("""
                INSERT OR IGNORE INTO ohlcv 
                (symbol, open_time, open, high, low, close, volume, close_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                int(row['open_time']),
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row['volume']),
                int(row['close_time']) if 'close_time' in row else int(row['open_time'])
            ))
        except Exception as e:
            print(f"Error saving row: {e}")
    
    conn.commit()
    conn.close()

def save_order_book(symbol, bids, asks, db_path: str = DB_PATH):
    """Save order book snapshot."""
    conn = sqlite3.connect(db_path)
    timestamp = int(time.time() * 1000)
    
    conn.execute(
        "INSERT INTO order_book_snapshots (symbol, timestamp, bids, asks) VALUES (?,?,?,?)",
        (symbol, timestamp, json.dumps(bids), json.dumps(asks))
    )
    
    conn.commit()
    conn.close()

def save_trade(data: dict, db_path: str = DB_PATH):
    """Save trade data."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO live_trades (symbol, price, quantity, trade_time, is_buyer_mm) VALUES (?,?,?,?,?)",
        (data["s"], float(data["p"]), float(data["q"]), data["T"], int(data["m"]))
    )
    conn.commit()
    conn.close()

def save_book_ticker(data: dict, db_path: str = DB_PATH):
    """Save book ticker data."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO live_book_ticker (symbol, timestamp, best_bid, best_ask, bid_qty, ask_qty) VALUES (?,?,?,?,?,?)",
        (
            data["s"],
            int(time.time() * 1000),
            float(data["b"]),
            float(data["a"]),
            float(data["B"]),
            float(data["A"]),
        )
    )
    conn.commit()
    conn.close()
"""
Database utilities for CryptoLens
"""

import sqlite3
import json
import time

DB_PATH = "crypto_data.db"

def init_db(db_path: str = DB_PATH):
    """Initialize database tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # OHLCV table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            open_time   INTEGER NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      REAL,
            close_time  INTEGER,
            UNIQUE(symbol, open_time)
        )
    """)

    # Order book snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_book_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            timestamp   INTEGER NOT NULL,
            bids        TEXT,
            asks        TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {db_path}")
