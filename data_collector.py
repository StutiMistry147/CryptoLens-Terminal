"""
Fetches historical OHLCV data from Binance REST API
and stores it in a local SQLite database.
"""

import requests
import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Import database utilities
from database import init_db, save_ohlcv

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BINANCE_BASE = "https://api.binance.com"
DB_PATH = "crypto_data.db"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT"]
INTERVAL = "1h"   # 1m, 5m, 15m, 1h, 4h, 1d
LOOKBACK_DAYS = 30


# ─── DATABASE SETUP ────────────────────────────────────────────────────────────
def init_db_old(db_path: str = DB_PATH):
    """Create tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_book_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            timestamp   INTEGER NOT NULL,
            bids        TEXT,   -- JSON string
            asks        TEXT    -- JSON string
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Tables ready.")


# ─── BINANCE REST HELPERS ───────────────────────────────────────────────────────
def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> list:
    """
    Fetch candlestick (OHLCV) data from Binance.
    Returns raw list of kline arrays.
    """
    url = f"{BINANCE_BASE}/api/v3/klines"
    all_klines = []
    current_start = start_ms

    while current_start < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ms,
            "limit": 1000,   # max per request
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            all_klines.extend(data)
            # next batch starts after last candle's close time
            current_start = data[-1][6] + 1
            time.sleep(0.2)   # respect rate limits
        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    return all_klines


def klines_to_df(klines: list, symbol: str) -> pd.DataFrame:
    """Convert raw Binance kline list to a clean DataFrame."""
    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]
    df = pd.DataFrame(klines, columns=columns)
    df["symbol"] = symbol
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)
    df["open_time"] = df["open_time"].astype(int)
    df["close_time"] = df["close_time"].astype(int)
    return df[["symbol", "open_time", "open", "high", "low", "close", "volume", "close_time"]]


def save_ohlcv_old(df: pd.DataFrame, db_path: str = DB_PATH):
    """Insert OHLCV rows, ignoring duplicates."""
    conn = sqlite3.connect(db_path)
    df.to_sql("ohlcv", conn, if_exists="append", index=False, method="multi")
    conn.commit()
    conn.close()


def fetch_order_book(symbol: str, limit: int = 20) -> dict:
    """Fetch current order book snapshot."""
    url = f"{BINANCE_BASE}/api/v3/depth"
    try:
        resp = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching order book: {e}")
        return {"bids": [], "asks": []}


def save_order_book(symbol: str, book: dict, db_path: str = DB_PATH):
    """Save an order book snapshot to DB."""
    import json
    conn = sqlite3.connect(db_path)
    ts = int(time.time() * 1000)
    conn.execute(
        "INSERT INTO order_book_snapshots (symbol, timestamp, bids, asks) VALUES (?,?,?,?)",
        (symbol, ts, json.dumps(book["bids"]), json.dumps(book["asks"]))
    )
    conn.commit()
    conn.close()


# ─── MAIN COLLECTION FLOW ──────────────────────────────────────────────────────
def collect_historical(symbols=SYMBOLS, days=LOOKBACK_DAYS, interval=INTERVAL):
    init_db_old()
    end_ms = int(time.time() * 1000)
    start_ms = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    for symbol in symbols:
        print(f"[{symbol}] Fetching {days} days of {interval} candles...")
        try:
            klines = fetch_klines(symbol, interval, start_ms, end_ms)
            if klines:
                df = klines_to_df(klines, symbol)
                save_ohlcv_old(df)
                print(f"[{symbol}] Saved {len(df)} candles.")
            else:
                print(f"[{symbol}] No data received.")
        except Exception as e:
            print(f"[{symbol}] ERROR: {e}")


def collect_order_books(symbols=SYMBOLS):
    """Take a single order book snapshot for each symbol."""
    init_db_old()
    for symbol in symbols:
        try:
            book = fetch_order_book(symbol)
            if book and book.get("bids") and book.get("asks"):
                save_order_book(symbol, book)
                print(f"[{symbol}] Order book snapshot saved.")
            else:
                print(f"[{symbol}] No order book data.")
        except Exception as e:
            print(f"[{symbol}] ERROR: {e}")


def load_ohlcv(symbol: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Load OHLCV data from DB into a DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT * FROM ohlcv WHERE symbol=? ORDER BY open_time ASC",
        conn, params=(symbol,)
    )
    conn.close()
    if len(df) > 0:
        df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Collecting Historical OHLCV Data ===")
    collect_historical()

    print("\n=== Collecting Order Book Snapshots ===")
    collect_order_books()

    print("\n=== Preview: BTC Data ===")
    df = load_ohlcv("BTCUSDT")
    if len(df) > 0:
        print(df.tail(5).to_string(index=False))
    else:
        print("No data available yet.")
