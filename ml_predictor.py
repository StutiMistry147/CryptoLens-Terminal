"""
Machine Learning Predictor for CryptoLens
Trains a PyTorch LSTM model with Order Book Imbalance and HMM Regime features 
to predict next candle price.
"""

import sqlite3
import numpy as np
import pandas as pd
import warnings
import json
import os
warnings.filterwarnings("ignore")

from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
import joblib
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

DB_PATH = "crypto_data.db"
SYMBOL = "BTCUSDT"
PREDICT_STEPS = 1   # predict N candles ahead
SEQ_LEN = 30        # Lookback window for LSTM

# ─── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_ohlcv(symbol: str = SYMBOL, db_path: str = DB_PATH) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            "SELECT * FROM ohlcv WHERE symbol=? ORDER BY open_time ASC",
            conn, params=(symbol,)
        )
        conn.close()
        if len(df) == 0:
            print(f"No data found for {symbol}. Generating synthetic data for testing.")
            return generate_synthetic_data(symbol)
        
        df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("datetime", inplace=True)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return generate_synthetic_data(symbol)


def load_order_book_data(symbol: str, db_path: str = DB_PATH) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            "SELECT timestamp, bids, asks FROM order_book_snapshots WHERE symbol=? ORDER BY timestamp ASC", 
            conn, params=(symbol,)
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading order book data: {e}")
        return pd.DataFrame()


def compute_obi(bids_str, asks_str, levels=5):
    try:
        bids = json.loads(bids_str)[:levels]
        asks = json.loads(asks_str)[:levels]
        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        if bid_vol + ask_vol == 0: return 0.5
        return bid_vol / (bid_vol + ask_vol)
    except:
        return 0.5


def generate_synthetic_data(symbol: str, n: int = 1500) -> pd.DataFrame:
    """Generate synthetic data for testing when no real data exists."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    
    returns = np.random.randn(n) * 0.02
    price = 50000 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "open": price * (1 + np.random.randn(n) * 0.005),
        "high": price * (1 + np.abs(np.random.randn(n)) * 0.01),
        "low": price * (1 - np.abs(np.random.randn(n)) * 0.01),
        "close": price,
        "volume": np.abs(np.random.randn(n)) * 1000 + 5000,
    }, index=dates)
    
    df["symbol"] = symbol
    df["open_time"] = dates.astype(np.int64) // 10**6
    return df


# ─── TECHNICAL INDICATORS & FEATURES ───────────────────────────────────────────
def add_technical_indicators(df: pd.DataFrame, is_training: bool=True) -> pd.DataFrame:
    """Add RSI, MACD, Bollinger Bands, Order Book Imbalance, and Regime features."""
    df = df.copy()
    close = df["close"]

    # 1. RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / (loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    # 2. MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # 3. Bollinger Bands
    sma20 = close.rolling(20, min_periods=20).mean()
    std20 = close.rolling(20, min_periods=20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20
    df["bb_width"] = df["bb_upper"] - df["bb_lower"]
    df["bb_position"] = (close - df["bb_lower"]) / (df["bb_width"] + 1e-9)

    # 4. Order Book Imbalance (OBI)
    symbol = df["symbol"].iloc[0] if "symbol" in df.columns else SYMBOL
    ob_df = load_order_book_data(symbol)
    if len(ob_df) > 0:
        ob_df['obi'] = ob_df.apply(lambda row: compute_obi(row['bids'], row['asks'], 5), axis=1)
        ob_df['datetime'] = pd.to_datetime(ob_df["timestamp"], unit="ms")
        ob_df = ob_df.sort_values("datetime").reset_index(drop=True)
        
        df = df.sort_index()
        df_merged = pd.merge_asof(
            df, 
            ob_df[['datetime', 'obi']], 
            left_index=True, 
            right_on='datetime', 
            direction='backward'
        )
        df_merged.set_index(df.index, inplace=True)
        df["obi"] = df_merged["obi"].fillna(0.5)
    else:
        df["obi"] = 0.5  # Neutral imbalance
        
    # 5. Volatility (for HMM)
    df['returns'] = df['close'].pct_change().fillna(0)
    df['volatility'] = df['returns'].rolling(window=10).std().fillna(0)

    # 6. HMM Regime Detection
    hmm_path = os.path.join(os.path.dirname(__file__), "hmm_model.pkl")
    X_hmm = df[['returns', 'volatility']].values
    
    if is_training:
        hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
        try:
            hmm.fit(X_hmm)
            joblib.dump(hmm, hmm_path)
            df["regime"] = hmm.predict(X_hmm)
        except:
            df["regime"] = 0
    else:
        if os.path.exists(hmm_path):
            hmm = joblib.load(hmm_path)
            try:
                df["regime"] = hmm.predict(X_hmm)
            except:
                df["regime"] = 0
        else:
            df["regime"] = 0

    # Target: future price
    df["target"] = close.shift(-PREDICT_STEPS)

    return df.dropna()


# ─── LSTM MODEL ────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal",
    "bb_upper", "bb_lower", "bb_width", "bb_position",
    "obi", "regime"
]

class CryptoLSTM(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(CryptoLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

def create_sequences(X, y=None, seq_length=SEQ_LEN):
    xs, ys = [], []
    for i in range(len(X) - seq_length):
        xs.append(X.iloc[i:(i + seq_length)].values)
        if y is not None:
            ys.append(y.iloc[i + seq_length])
    return np.array(xs), np.array(ys) if y is not None else None


def train_lstm(df: pd.DataFrame):
    """Train LSTM to predict next candle's close price."""
    print("\n=== Training PyTorch LSTM Model ===")
    
    if len(df) < SEQ_LEN + 10:
        print("Not enough data for training.")
        return None, None, None, None
        
    X = df[FEATURE_COLS]
    y = df["target"]

    # Chronological split
    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    # Scaling
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()

    X_train_scaled = pd.DataFrame(scaler_X.fit_transform(X_train), columns=FEATURE_COLS)
    X_test_scaled = pd.DataFrame(scaler_X.transform(X_test), columns=FEATURE_COLS)
    
    y_train_scaled = pd.Series(scaler_y.fit_transform(y_train.values.reshape(-1, 1)).flatten())
    y_test_scaled = pd.Series(scaler_y.transform(y_test.values.reshape(-1, 1)).flatten())

    # Create Sequences
    X_train_seq, y_train_seq = create_sequences(X_train_scaled, y_train_scaled)
    X_test_seq, y_test_seq = create_sequences(X_test_scaled, y_test_scaled)
    
    if len(X_train_seq) == 0 or len(X_test_seq) == 0:
        print("Sequence generation resulted in empty arrays. Check dataset size.")
        return None, None, None, None

    train_data = TensorDataset(torch.Tensor(X_train_seq), torch.Tensor(y_train_seq))
    train_loader = DataLoader(train_data, batch_size=32, shuffle=False)

    # Initialize Model, Loss, Optimizer
    model = CryptoLSTM(input_size=len(FEATURE_COLS))
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Training Loop
    epochs = 20
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs.squeeze(), batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        if (epoch + 1) % 5 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss/len(train_loader):.4f}")

    # Evaluation
    model.eval()
    with torch.no_grad():
        test_outputs = model(torch.Tensor(X_test_seq)).numpy()
        
    preds = scaler_y.inverse_transform(test_outputs)
    actuals = y_test.values[SEQ_LEN:]
    
    # Calculate Metrics
    mae = np.mean(np.abs(preds.flatten() - actuals))
    rmse = np.sqrt(np.mean((preds.flatten() - actuals)**2))
    
    # Directional Accuracy against current close price
    actual_direction = np.sign(actuals - X_test["close"].values[SEQ_LEN:])
    pred_direction = np.sign(preds.flatten() - X_test["close"].values[SEQ_LEN:])
    directional_acc = np.mean(actual_direction == pred_direction)

    print(f"\n[LSTM Results]")
    print(f"  MAE:               ${mae:,.2f}")
    print(f"  RMSE:              ${rmse:,.2f}")
    print(f"  Directional Acc:   {directional_acc:.1%}")

    # Save models & scalers
    base_dir = os.path.dirname(__file__)
    torch.save(model.state_dict(), os.path.join(base_dir, "lstm_model.pth"))
    joblib.dump(scaler_X, os.path.join(base_dir, "scaler_X.pkl"))
    joblib.dump(scaler_y, os.path.join(base_dir, "scaler_y.pkl"))
    print(f"  Models saved successfully.")

    # Generate full dataset test predictions to match expected API
    # Creating a series of predictions aligned with original index
    full_preds = pd.Series(index=y_test.index, dtype=float)
    full_preds.iloc[SEQ_LEN:] = preds.flatten()
    
    return model, X_test, y_test, full_preds


# ─── LIVE PREDICTION ───────────────────────────────────────────────────────────
def predict_next_price(latest_df: pd.DataFrame) -> float:
    """Predict next candle close using the trained PyTorch LSTM."""
    try:
        base_dir = os.path.dirname(__file__)
        model_path = os.path.join(base_dir, "lstm_model.pth")
        
        if not os.path.exists(model_path):
            print("No model found. Train first with ml_predictor.py")
            return None
            
        scaler_X = joblib.load(os.path.join(base_dir, "scaler_X.pkl"))
        scaler_y = joblib.load(os.path.join(base_dir, "scaler_y.pkl"))
        
        model = CryptoLSTM(input_size=len(FEATURE_COLS))
        # Ensure we use weights_only=True to prevent warnings on modern PyTorch, or standard map_location
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
        model.eval()
        
        df_with_features = add_technical_indicators(latest_df, is_training=False)
        
        if len(df_with_features) < SEQ_LEN:
            print("Not enough data for sequence prediction")
            return None
            
        recent_data = df_with_features[FEATURE_COLS].iloc[-SEQ_LEN:]
        scaled_data = scaler_X.transform(recent_data)
        
        tensor_data = torch.Tensor(scaled_data).unsqueeze(0) # Add batch dimension
        
        with torch.no_grad():
            pred_scaled = model(tensor_data).numpy()
            
        prediction = scaler_y.inverse_transform(pred_scaled)[0][0]
        current = latest_df["close"].iloc[-1]
        change = (prediction - current) / current * 100
        print(f"\n[Prediction] Current: ${current:,.2f} → Next: ${prediction:,.2f} ({change:+.2f}%)")
        return prediction
    except Exception as e:
        print(f"Prediction error: {e}")
        return None


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Loading Data ===")
    raw_df = load_ohlcv(SYMBOL)
    print(f"Loaded {len(raw_df)} rows for {SYMBOL}")

    print("\n=== Engineering Features (OB Imbalance & Regime) ===")
    df = add_technical_indicators(raw_df, is_training=True)
    print(f"Feature matrix shape: {df.shape}")

    if len(df) > 0:
        lstm_model, X_test, y_test, lstm_preds = train_lstm(df)

        if lstm_model is not None:
            predict_next_price(raw_df)
    else:
        print("No data available for training.")
