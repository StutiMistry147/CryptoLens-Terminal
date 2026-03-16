# CryptoLens Terminal

A professional-grade cryptocurrency analytics and paper trading platform 
that combines real-time market data, machine learning price prediction, 
and automated trading into a single terminal-style dashboard.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

CryptoLens Terminal streams live market data from Binance, runs ML models 
to predict price movements, and simulates trading strategies — all inside 
a Bloomberg-style terminal UI.

---

## Features

- **Real-Time Data Streaming** — Live OHLCV and order book data via 
  Binance WebSocket API
- **ML Price Prediction** — PyTorch LSTM model trained on engineered 
  technical indicators (RSI, MACD, Bollinger Bands)
- **Market Regime Detection** — Hidden Markov Models (HMM) to identify 
  bull, bear, and sideways market conditions
- **Order Book Analysis** — Imbalance detection for liquidity assessment
- **Paper Trading** — Automated strategy execution via Alpaca API with 
  PnL tracking
- **Walk-Forward Validation** — Robust out-of-sample model evaluation
- **Terminal UI** — Bloomberg-style dashboard built with Streamlit and 
  Plotly

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python |
| Dashboard | Streamlit + Plotly |
| Data | Binance REST + WebSocket API |
| Trading | Alpaca API |
| ML Models | PyTorch, scikit-learn, hmmlearn |
| Storage | SQLite |
| Data Processing | Pandas, NumPy |

---

## Architecture
```
Binance WebSocket → Data Collector → SQLite
                                        ↓
                              ML Predictor (LSTM + HMM)
                                        ↓
                          Alpaca Paper Trading Engine
                                        ↓
                          Streamlit Dashboard (main.py)
```

---

## Getting Started

### Prerequisites
- Python 3.8+
- Binance API key (free account)
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

# 2. Start data collection
python data_collector.py

# 3. Train the ML model
python ml_predictor.py

# 4. Start live WebSocket feed
python websocket_feed.py

# 5. Launch the dashboard
streamlit run main.py
```

---

## Project Structure
```
cryptolens-terminal/
├── main.py              # Streamlit dashboard entry point
├── database.py          # SQLite schema and initialization
├── data_collector.py    # Binance REST API data fetcher
├── websocket_feed.py    # Binance WebSocket live feed
├── ml_predictor.py      # LSTM + HMM model training
├── requirements.txt     # Dependencies
└── README.md
```

---

## Author

Stuti Mistry — Computer Science Student, Constructor University
[LinkedIn](your-linkedin-url) | [GitHub](https://github.com/StutiMistry147)
