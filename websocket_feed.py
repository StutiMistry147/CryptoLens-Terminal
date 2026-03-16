"""
WebSocket feed for live data
Connects to Binance WebSocket streams for real-time trades and order books
"""

import asyncio
import json
import sqlite3
import time
import websockets
from datetime import datetime
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Import database utilities
from database import init_db, save_trade, save_book_ticker

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BINANCE_WS = "wss://stream.binance.com:9443/stream"
SYMBOLS = ["btcusdt", "ethusdt", "bnbusdt", "solusdt"]
DB_PATH = "crypto_data.db"


# ─── DATABASE ──────────────────────────────────────────────────────────────────
def init_live_tables(db_path: str = DB_PATH):
    """Initialize live data tables."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS live_trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT,
            price       REAL,
            quantity    REAL,
            trade_time  INTEGER,
            is_buyer_mm INTEGER
        )
    """)
    conn.execute("""
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


def save_trade_old(data: dict, db_path: str = DB_PATH):
    """Save trade data."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO live_trades (symbol, price, quantity, trade_time, is_buyer_mm) VALUES (?,?,?,?,?)",
        (data["s"], float(data["p"]), float(data["q"]), data["T"], int(data["m"]))
    )
    conn.commit()
    conn.close()


def save_book_ticker_old(data: dict, db_path: str = DB_PATH):
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


# ─── WEBSOCKET HANDLER ─────────────────────────────────────────────────────────
async def stream_data(symbols: list = SYMBOLS, duration_seconds: int = 60):
    """
    Streams trade + book ticker for each symbol.
    Runs for `duration_seconds` then exits (set to None to run forever).
    """
    # Build combined stream URL
    streams = []
    for sym in symbols:
        streams.append(f"{sym}@trade")
        streams.append(f"{sym}@bookTicker")

    url = f"{BINANCE_WS}?streams=" + "/".join(streams)
    print(f"[WS] Connecting to: {url}")

    start = time.time()
    message_count = 0
    
    try:
        async with websockets.connect(url) as ws:
            print("[WS] Connected! Streaming data...\n")
            async for message in ws:
                envelope = json.loads(message)
                stream_name = envelope.get("stream", "")
                data = envelope.get("data", {})
                event_type = data.get("e", "")

                if event_type == "trade":
                    price = float(data["p"])
                    qty = float(data["q"])
                    ts = datetime.fromtimestamp(data["T"] / 1000).strftime("%H:%M:%S")
                    print(f"[TRADE] {data['s']:8} | {ts} | Price: {price:8,.2f} | Qty: {qty:.4f}")
                    save_trade_old(data)
                    message_count += 1

                elif stream_name.endswith("@bookTicker") or event_type == "bookTicker":
                    bid = float(data["b"])
                    ask = float(data["a"])
                    spread = ask - bid
                    spread_pct = (spread / bid) * 100
                    print(f"[BOOK]  {data['s']:8} | Bid: {bid:8,.2f} | Ask: {ask:8,.2f} | Spread: {spread_pct:.4f}%")
                    save_book_ticker_old(data)
                    message_count += 1

                # Stop after duration
                if duration_seconds and (time.time() - start) > duration_seconds:
                    print(f"\n[WS] {duration_seconds}s elapsed. Stopping stream.")
                    print(f"[WS] Received {message_count} messages.")
                    break
                    
    except websockets.exceptions.ConnectionClosed:
        print("[WS] Connection closed")
    except Exception as e:
        print(f"[WS] Error: {e}")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Initialising Live Tables ===")
    init_live_tables()

    print("\n=== Starting Live WebSocket Feed (60 seconds) ===")
    print("Press Ctrl+C to stop early.\n")
    try:
        asyncio.run(stream_data(duration_seconds=60))
    except KeyboardInterrupt:
        print("\n[WS] Stream stopped by user.")
