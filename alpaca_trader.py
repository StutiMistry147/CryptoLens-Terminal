"""
Live Event-Driven Trading Loop
Connects to Alpaca's Paper Trading API, gets the latest ML signal, and executes market orders.
"""

import os
import time
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.common.exceptions import APIError

import ml_predictor as ml

# Alpaca API configuration - recommend setting these in your environment variables
API_KEY = os.environ.get("APCA_API_KEY_ID", "your_api_key_here")
SECRET_KEY = os.environ.get("APCA_API_SECRET_KEY", "your_secret_key_here")

# Initialize Alpaca Trading Client (Paper Trading)
trade_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# Main trading symbol (Ensure format matches Alpaca's crypto format, typically BTC/USD)
TRADE_SYMBOL = "BTC/USD"
DATA_SYMBOL = "BTCUSDT"

def get_current_position():
    """Retrieve the current open position for the symbol."""
    try:
        if API_KEY == "your_api_key_here":
            return {"qty": 0.0, "unrealized_pl": 0.0, "avg_entry_price": 0.0}
            
        position = trade_client.get_open_position(TRADE_SYMBOL)
        return {
            "qty": float(position.qty),
            "unrealized_pl": float(position.unrealized_pl),
            "avg_entry_price": float(position.avg_entry_price)
        }
    except APIError as e:
        # If no position exists, Alpaca raises a 404 APIError
        return {"qty": 0.0, "unrealized_pl": 0.0, "avg_entry_price": 0.0}
    except Exception as e:
        print(f"[ERROR] Could not fetch position: {e}")
        return {"qty": 0.0, "unrealized_pl": 0.0, "avg_entry_price": 0.0}


def execute_order(side: OrderSide, qty: float = 0.01):
    """Submits a market order to Alpaca."""
    if API_KEY == "your_api_key_here":
        print("[MOCK EXECUTION] API Keys not set. Mocking order submission.")
        return
        
    try:
        order_request = MarketOrderRequest(
            symbol=TRADE_SYMBOL,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.GTC
        )
        order = trade_client.submit_order(order_data=order_request)
        print(f"[ORDER EXECUTED] {order.side.name} {order.qty} {order.symbol} @ MARKET")
    except Exception as e:
        print(f"[ORDER FAILED] Error executing {side.name} order: {e}")


def run_trading_loop(interval_seconds=60, confidence_threshold=0.05):
    """
    Main event loop.
    1. Fetch latest data
    2. Get ML signal
    3. Check position
    4. Execute trade if signal > threshold
    """
    print(f"=== Starting Live Trading Loop for {TRADE_SYMBOL} ===")
    print(f"Polling Interval: {interval_seconds}s | Threshold: ±{confidence_threshold}%\n")
    
    while True:
        try:
            # 1. Load latest data directly through the ML Predictor pipeline
            df = ml.load_ohlcv(DATA_SYMBOL, ml.DB_PATH)
            
            if len(df) < ml.SEQ_LEN:
                print("[WAITING] Gathering sufficient history for LSTM sequences...")
                time.sleep(interval_seconds)
                continue
                
            current_price = df['close'].iloc[-1]
            
            # 2. Get the next price prediction from the PyTorch LSTM
            prediction = ml.predict_next_price(df)
            
            if prediction is None:
                print("[SKIPPING] Prediction failed.")
                time.sleep(interval_seconds)
                continue
                
            pred_change_pct = ((prediction - current_price) / current_price) * 100
            
            # 3. Check current Alpaca position
            position = get_current_position()
            
            print(f"Price: ${current_price:,.2f} | Pred: ${prediction:,.2f} ({pred_change_pct:+.2f}%) | Pos: {position['qty']} @ ${position['avg_entry_price']:.2f}")
            
            # 4. Trading Logic
            if pred_change_pct > confidence_threshold:
                print(">>> SIGNAL: BUY")
                # Go long if we aren't already long
                if position["qty"] <= 0:
                    # Close short if necessary, and open long
                    qty_to_buy = 0.01 + abs(position["qty"])
                    execute_order(OrderSide.BUY, qty_to_buy)
                else:
                    print("Already hold LONG position.")
                    
            elif pred_change_pct < -confidence_threshold:
                print(">>> SIGNAL: SELL")
                # Go short if we aren't already short
                if position["qty"] >= 0:
                    # Close long if necessary, and open short
                    qty_to_sell = 0.01 + abs(position["qty"])
                    execute_order(OrderSide.SELL, qty_to_sell)
                else:
                    print("Already hold SHORT position.")
                    
            else:
                print(">>> SIGNAL: HOLD (Below Confidence Threshold)")
                
        except Exception as e:
            print(f"[ERROR] Trading loop exception: {e}")
            
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_trading_loop()
