# CryptoLens Terminal

A cryptocurrency analytics platform that streams live Binance market data,
engineers technical indicators as ML features, and runs a PyTorch LSTM with
Hidden Markov Model regime detection to predict next-candle price movement —
visualized through a Streamlit dashboard with paper trading execution via Alpaca.

_> Without API keys the dashboard runs in demo mode with synthetic data._
_> Live features require valid Binance and Alpaca keys._

---
## Architecture
```
Binance REST API  ──→  data_collector.py  ──→  SQLite (crypto_data.db)
Binance WebSocket ──→  websocket_feed.py  ──→  SQLite (live trades + order book)
                                                      │
                                               ml_predictor.py
                                          (LSTM + HMM + OBI features)
                                                      │
                                           alpaca_trader.py
                                        (paper trading execution)
                                                      │
                                              main.py (Streamlit)
```
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/ae976e5c-a7c4-4169-a37e-a670f9f62e5a" />

---

## ML Pipeline
**Feature Engineering**
- RSI (14), MACD (12/26/9), Bollinger Bands (20)
- Order Book Imbalance (OBI) — computed from top-5 bid/ask levels,
  merged with OHLCV using `merge_asof` for accurate time alignment
- Market Regime — 3-state Gaussian HMM fitted on returns and rolling
  volatility to detect bull, bear, and sideways conditions

**Model**
- 2-layer PyTorch LSTM (hidden=64, dropout=0.2, seq_len=30)
- Chronological 80/20 train/test split (no data leakage)
- StandardScaler fitted on training data only
- Evaluated on MAE, RMSE, and directional accuracy

**Live Prediction**
- Loads saved model weights and scalers
- Feeds latest 30 candles through the full feature pipeline
- Outputs next-candle price prediction with percentage change signal

---

## Tech Stack

| Component | Technology |
|---|---|
| Dashboard | Streamlit + Plotly |
| ML Models | PyTorch, scikit-learn, hmmlearn |
| Data | Binance REST + WebSocket API |
| Paper Trading | Alpaca API |
| Storage | SQLite |
| Data Processing | Pandas, NumPy |

---

## Getting Started

### Prerequisites
- Python 3.8+
- Binance API key (free account, read-only is sufficient)
- Alpaca API key (free paper trading account)


### Installation
```bash
git clone https://github.com/StutiMistry147/cryptolens-terminal.git
cd CryptoLens-Terminal
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Platform

Run each step in order:
```bash
# 1. Initialize the database
python database.py

# 2. Collect historical OHLCV + order book data
python data_collector.py

# 3. Start live WebSocket feed (optional, 60s by default)
python websocket_feed.py

# 4. Train the LSTM + HMM model
python ml_predictor.py

# 5. Launch the dashboard
streamlit run main.py
```
---
