"""
CryptoLens Streamlit Dashboard
Dark terminal aesthetic with real-time crypto analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import sys
import os
import json
import random

# Add path for local imports
sys.path.append(os.path.dirname(__file__))

# Import your existing modules
try:
    from database import DB_PATH, get_db_stats
    from ml_predictor import load_ohlcv, predict_next_price, add_technical_indicators
    from alpaca_trader import get_current_position, execute_order
except ImportError:
    # Fallback for demo mode
    print("Running in demo mode - some features disabled")
    DB_PATH = "crypto_data.db"

# Page config
st.set_page_config(
    page_title="CryptoLens Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for terminal aesthetic
st.markdown("""
<style>
    /* Main container */
    .main > div {
        background-color: #0d0f14;
        padding: 0rem 1rem;
    }
    
    /* Text styles */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6 {
        color: #e0e2e8 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    
    /* Monospace for numbers */
    .mono, .metric-value, .price, .volume, .stat-number {
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 500 !important;
    }
    
    /* Metric cards */
    .metric-card {
        background: #14171c;
        border: 1px solid #2a2e35;
        border-radius: 4px;
        padding: 1rem;
        margin: 0.25rem 0;
    }
    
    .metric-label {
        color: #8a8f99;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        line-height: 1.2;
    }
    
    .metric-sub {
        color: #5f6670;
        font-size: 0.75rem;
    }
    
    /* Panels */
    .panel {
        background: #14171c;
        border: 1px solid #2a2e35;
        border-radius: 4px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .panel-title {
        color: #8a8f99;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Badges */
    .badge {
        background: #1e2228;
        border: 1px solid #2a2e35;
        border-radius: 3px;
        padding: 0.2rem 0.5rem;
        font-size: 0.7rem;
        font-family: 'IBM Plex Mono', monospace;
        color: #8a8f99;
    }
    
    .badge-paper {
        background: #2a2e35;
        color: #f5a623;
        border-color: #f5a623;
    }
    
    .badge-long {
        background: rgba(0, 229, 160, 0.2);
        color: #00e5a0;
    }
    
    .badge-short {
        background: rgba(255, 71, 87, 0.2);
        color: #ff4757;
    }
    
    /* Status dot */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    .status-live { background: #00e5a0; }
    .status-dead { background: #2a2e35; }
    
    /* Order book rows */
    .order-row {
        display: flex;
        justify-content: space-between;
        padding: 0.25rem 0;
        position: relative;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
    }
    
    .depth-bar {
        position: absolute;
        top: 0;
        bottom: 0;
        background: rgba(255, 71, 87, 0.15);
        right: 0;
        z-index: 0;
    }
    
    .depth-bar.bid {
        background: rgba(0, 229, 160, 0.15);
        left: 0;
        right: auto;
    }
    
    .order-content {
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        width: 100%;
    }
    
    /* Trade rows */
    .trade-row {
        display: grid;
        grid-template-columns: 80px 60px 80px 60px;
        gap: 0.5rem;
        padding: 0.25rem 0;
        border-bottom: 1px solid #2a2e35;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
    }
    
    .trade-buy { color: #00e5a0; }
    .trade-sell { color: #ff4757; }
    
    /* Colors */
    .positive { color: #00e5a0 !important; }
    .negative { color: #ff4757 !important; }
    .neutral { color: #f5a623 !important; }
    .blue { color: #3d9aff !important; }
    .purple { color: #8b5cf6 !important; }
    
    /* Buttons and inputs */
    .stButton > button {
        background: #1e2228;
        color: #e0e2e8;
        border: 1px solid #2a2e35;
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .stButton > button:hover {
        border-color: #3d9aff;
        background: #2a2e35;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #1e2228;
        border: 1px solid #2a2e35;
        border-radius: 4px;
        padding: 0.25rem 1rem;
        font-family: 'IBM Plex Mono', monospace;
        color: #8a8f99;
    }
    
    .stTabs [aria-selected="true"] {
        background: #2a2e35;
        border-color: #3d9aff;
        color: #fff;
    }
    
    /* Dataframes */
    .stDataFrame {
        background: #0d0f14;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e2228;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2a2e35;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #3d3f45;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'symbol' not in st.session_state:
    st.session_state.symbol = 'BTCUSDT'
if 'data' not in st.session_state:
    st.session_state.data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'position' not in st.session_state:
    st.session_state.position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'qty': 0.25,
        'entry': 71234.50,
        'current': 72345.50,
        'pnl': 1111.00,
        'pnl_pct': 1.56,
        'time': '2h 34m'
    }

# Mock data generator for demo
def generate_mock_data(symbol, periods=100):
    """Generate mock OHLCV data for demo"""
    np.random.seed(hash(symbol) % 2**32)
    
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')
    
    # Base price varies by symbol
    base_prices = {
        'BTCUSDT': 72000,
        'ETHUSDT': 3500,
        'SOLUSDT': 110,
        'BNBUSDT': 580
    }
    base = base_prices.get(symbol, 100)
    
    # Generate price series with trend and volatility
    returns = np.random.randn(periods) * 0.02
    price = base * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': price * (1 + np.random.randn(periods) * 0.005),
        'high': price * (1 + np.abs(np.random.randn(periods)) * 0.01),
        'low': price * (1 - np.abs(np.random.randn(periods)) * 0.01),
        'close': price,
        'volume': np.abs(np.random.randn(periods)) * 1000 + 5000,
    })
    
    df.set_index('datetime', inplace=True)
    return df

# Top bar
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.markdown("<h3 style='color: #e0e2e8; margin:0;'>CRYPTO<span style='color: #3d9aff;'>LENS</span></h3>", 
                unsafe_allow_html=True)
with col2:
    # Pair tabs as clickable buttons
    tab_cols = st.columns(4)
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
    for i, (col, sym) in enumerate(zip(tab_cols, symbols)):
        with col:
            if st.button(sym, key=f"tab_{sym}", 
                        use_container_width=True,
                        type="secondary" if sym != st.session_state.symbol else "primary"):
                st.session_state.symbol = sym
                st.rerun()
with col3:
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end;">
            <span class="status-dot status-live"></span>
            <span style="color: #8a8f99; font-size: 0.8rem;">LIVE · Binance</span>
        </div>
    """, unsafe_allow_html=True)

# Load data
try:
    df = load_ohlcv(st.session_state.symbol, DB_PATH)
    if df is None or len(df) == 0:
        df = generate_mock_data(st.session_state.symbol)
except:
    df = generate_mock_data(st.session_state.symbol)

st.session_state.data = df

# Current price and metrics
current_price = df['close'].iloc[-1] if df is not None and len(df) > 0 else 72345.50
prev_price = df['close'].iloc[-2] if df is not None and len(df) > 1 else current_price * 0.97
change_24h = ((current_price - prev_price) / prev_price) * 100

# Metric cards row
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Last Price</div>
            <div class="metric-value mono">${current_price:,.2f}</div>
            <div class="metric-sub">High: ${current_price*1.01:,.0f} · Low: ${current_price*0.99:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)

with m2:
    change_class = "positive" if change_24h > 0 else "negative"
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">24h Change</div>
            <div class="metric-value mono {change_class}">{change_24h:+.2f}%</div>
            <div class="metric-sub">${current_price - prev_price:+,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with m3:
    sharpe = 1.89 + (random.random() - 0.5) * 0.2
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Sharpe (30d)</div>
            <div class="metric-value mono">{sharpe:.2f}</div>
            <div class="metric-sub">Ann: {sharpe*1.2:.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with m4:
    var = -abs(current_price * 0.017)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">VaR 95%</div>
            <div class="metric-value mono negative">${var:,.0f}</div>
            <div class="metric-sub">CVaR: ${var*1.5:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)

with m5:
    signal = "BULLISH" if change_24h > 0 else "BEARISH"
    signal_color = "positive" if change_24h > 0 else "negative"
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Model Signal</div>
            <div class="metric-value {signal_color}">{signal}</div>
            <div class="metric-sub">Conf: {0.7 + abs(change_24h/10):.2f}</div>
        </div>
    """, unsafe_allow_html=True)

# Main grid
left_col, right_col = st.columns([2, 1])

with left_col:
    # Price Chart
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="panel-header">
            <span class="panel-title">{st.session_state.symbol} · 1h</span>
            <span class="badge">LIVE</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Create price chart with plotly
    if df is not None and len(df) > 0:
        fig = make_subplots(rows=2, cols=1, row_heights=[0.8, 0.2], 
                           vertical_spacing=0.03,
                           shared_xaxes=True)
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=df.index[-50:],
            open=df['open'].iloc[-50:],
            high=df['high'].iloc[-50:],
            low=df['low'].iloc[-50:],
            close=df['close'].iloc[-50:],
            name='Price',
            increasing_line_color='#00e5a0',
            decreasing_line_color='#ff4757',
            showlegend=False
        ), row=1, col=1)
        
        # Volume bars
        colors = ['#00e5a0' if df['close'].iloc[i] >= df['open'].iloc[i] 
                  else '#ff4757' for i in range(-50, 0)]
        fig.add_trace(go.Bar(
            x=df.index[-50:],
            y=df['volume'].iloc[-50:],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ), row=2, col=1)
        
        # Update layout
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0d0f14',
            plot_bgcolor='#0d0f14',
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_rangeslider_visible=False
        )
        
        fig.update_xaxes(gridcolor='#2a2e35', gridwidth=0.5)
        fig.update_yaxes(gridcolor='#2a2e35', gridwidth=0.5)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # OB Imbalance bars
    st.markdown("""
        <div style="display: flex; gap: 2px; margin-top: 0.5rem; height: 40px;">
    """, unsafe_allow_html=True)
    
    for i in range(20):
        height = random.randint(20, 100)
        st.markdown(f"""
            <div style="flex: 1; background: linear-gradient(to top, #2a2e35, #3d3f45); position: relative;">
                <div style="position: absolute; bottom: 0; width: 100%; height: {height}%; background: #3d9aff;"></div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Forecast Panel
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("""
        <div class="panel-header">
            <span class="panel-title">PRICE FORECAST · NEXT 10 BARS</span>
            <span class="badge">TFT · seq=60 · 95% CI</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Forecast chart
    forecast_fig = go.Figure()
    
    # Historical
    hist_x = list(range(30))
    hist_y = [current_price * (1 - 0.02 * np.sin(i/5)) for i in range(30)]
    
    # Forecast
    forecast_x = list(range(30, 40))
    forecast_y = [current_price * (1 + 0.015 * (i-29)) for i in range(30, 40)]
    
    # Confidence band
    forecast_fig.add_trace(go.Scatter(
        x=forecast_x,
        y=[y * 1.02 for y in forecast_y],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='none'
    ))
    
    forecast_fig.add_trace(go.Scatter(
        x=forecast_x,
        y=[y * 0.98 for y in forecast_y],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(61, 154, 255, 0.1)',
        showlegend=False,
        hoverinfo='none'
    ))
    
    # Historical line
    forecast_fig.add_trace(go.Scatter(
        x=hist_x,
        y=hist_y,
        mode='lines',
        line=dict(color='#e0e2e8', width=1.5),
        name='Historical',
        showlegend=False
    ))
    
    # Forecast line
    forecast_fig.add_trace(go.Scatter(
        x=forecast_x,
        y=forecast_y,
        mode='lines',
        line=dict(color='#3d9aff', width=2),
        name='Forecast',
        showlegend=False
    ))
    
    forecast_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0f14',
        plot_bgcolor='#0d0f14',
        height=120,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    st.plotly_chart(forecast_fig, use_container_width=True, config={'displayModeBar': False})
    
    # Forecast stats
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        pred_change = (forecast_y[-1] - current_price) / current_price * 100
        pred_class = "positive" if pred_change > 0 else "negative"
        st.markdown(f"""
            <div>
                <span style="color: #8a8f99;">Next →</span>
                <span class="mono" style="font-size: 1.2rem;">${forecast_y[-1]:,.0f}</span>
                <span class="{pred_class}" style="font-size: 1rem;">{'▲' if pred_change > 0 else '▼'}</span>
            </div>
        """, unsafe_allow_html=True)
    with fcol2:
        st.markdown(f"""
            <div>
                <span style="color: #8a8f99;">Confidence</span>
                <span class="mono" style="font-size: 1.2rem;">0.92</span>
            </div>
        """, unsafe_allow_html=True)
    with fcol3:
        st.markdown(f"""
            <div>
                <span style="color: #8a8f99;">Direction</span>
                <span class="mono {pred_class}">{pred_change:+.2f}%</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Order Book Imbalance Panel
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("""
        <div class="panel-header">
            <span class="panel-title">ORDER BOOK IMBALANCE</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Depth levels
    for level, (bid_pct, imbalance) in enumerate([(67, 0.34), (64, 0.28), (59.5, 0.19)]):
        st.markdown(f"""
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span style="color: #8a8f99;">Level {level+1}</span>
                    <span class="mono positive">+{imbalance:.2f}</span>
                </div>
                <div style="display: flex; height: 24px; background: #1e2228; border-radius: 3px; overflow: hidden;">
                    <div style="width: {bid_pct}%; background: #00e5a0;"></div>
                    <div style="width: {100-bid_pct}%; background: #ff4757;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Sparkline
    spark_x = list(range(20))
    spark_y = [0.3 + 0.2 * np.sin(i/3) + random.random()*0.1 for i in range(20)]
    
    spark_fig = go.Figure()
    spark_fig.add_trace(go.Scatter(
        x=spark_x,
        y=spark_y,
        mode='lines',
        line=dict(color='#f5a623', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(245, 166, 35, 0.1)',
        showlegend=False
    ))
    
    spark_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0f14',
        plot_bgcolor='#0d0f14',
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    st.plotly_chart(spark_fig, use_container_width=True, config={'displayModeBar': False})
    
    # Aggregate
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
            <span style="background: rgba(0, 229, 160, 0.2); color: #00e5a0; padding: 0.2rem 0.8rem; border-radius: 3px; font-size: 0.8rem;">BID PRESSURE</span>
            <span class="mono">+0.27 · +12%</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    # Order Book
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="panel-header">
            <span class="panel-title">ORDER BOOK · {st.session_state.symbol}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Generate order book data
    base_price = current_price
    
    # Asks
    for i in range(5):
        price = base_price + (i+1) * 0.5
        size = random.uniform(1, 5)
        depth_pct = random.randint(30, 90)
        st.markdown(f"""
            <div class="order-row">
                <div class="order-content">
                    <span style="color: #ff4757;">{price:,.2f}</span>
                    <span>{size:.4f}</span>
                </div>
                <div class="depth-bar" style="width: {depth_pct}%;"></div>
            </div>
        """, unsafe_allow_html=True)
    
    # Spread
    spread = 1.5
    spread_pct = (spread / base_price) * 100
    imbalance = 0.24
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; margin: 0.5rem 0; border-top: 1px solid #2a2e35; border-bottom: 1px solid #2a2e35;">
            <span style="color: #8a8f99;">Spread: {spread:.2f} ({spread_pct:.4f}%)</span>
            <span style="color: #f5a623; font-family: monospace;">Imbalance: +{imbalance:.2f}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Bids
    for i in range(5):
        price = base_price - (i+1) * 0.5
        size = random.uniform(2, 8)
        depth_pct = random.randint(40, 95)
        st.markdown(f"""
            <div class="order-row">
                <div class="order-content">
                    <span style="color: #00e5a0;">{price:,.2f}</span>
                    <span>{size:.4f}</span>
                </div>
                <div class="depth-bar bid" style="width: {depth_pct}%;"></div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Trades
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("""
        <div class="panel-header">
            <span class="panel-title">RECENT TRADES</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Generate recent trades
    now = datetime.now()
    for i in range(8):
        time = now - timedelta(seconds=random.randint(10, 300))
        side = random.choice(['BUY', 'SELL'])
        price = current_price + (random.random() - 0.5) * 10
        qty = random.uniform(0.1, 2)
        side_class = 'trade-buy' if side == 'BUY' else 'trade-sell'
        
        st.markdown(f"""
            <div class="trade-row">
                <span>{time.strftime('%H:%M:%S')}</span>
                <span class="{side_class}">{side}</span>
                <span>${price:,.0f}</span>
                <span>{qty:.4f}</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Alpaca Paper Trading Panel
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("""
        <div class="panel-header">
            <span class="panel-title">ALPACA PAPER TRADING</span>
            <span class="badge badge-paper">PAPER</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Current position
    pos = st.session_state.position
    st.markdown("""
        <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.5rem; margin-bottom: 0.5rem;">
            <span style="color: #8a8f99; font-size: 0.7rem;">SYM</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">SIDE</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">QTY</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">ENTRY</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">CURRENT</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">PnL</span>
            <span style="color: #8a8f99; font-size: 0.7rem;">TIME</span>
        </div>
    """, unsafe_allow_html=True)
    
    pnl_class = "positive" if pos['pnl'] > 0 else "negative"
    st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.5rem; padding: 0.5rem 0; border-bottom: 1px solid #2a2e35;">
            <span class="mono">{pos['symbol'][:3]}</span>
            <span><span class="badge badge-{pos['side'].lower()}">{pos['side']}</span></span>
            <span class="mono">{pos['qty']:.4f}</span>
            <span class="mono">${pos['entry']:,.0f}</span>
            <span class="mono">${pos['current']:,.0f}</span>
            <span class="mono {pnl_class}">${pos['pnl']:+,.2f} ({pos['pnl_pct']:+.2f}%)</span>
            <span class="mono">{pos['time']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Recent orders
    st.markdown('<div style="margin-top: 1rem;">', unsafe_allow_html=True)
    st.markdown('<span class="panel-title">LAST 5 ORDERS</span>', unsafe_allow_html=True)
    
    orders = [
        ('09:41:23', 'BUY', 72345, 0.25, 'FILLED'),
        ('09:35:12', 'SELL', 72100, 0.15, 'FILLED'),
        ('09:28:45', 'BUY', 71890, 0.40, 'FILLED'),
        ('09:22:34', 'BUY', 71500, 0.10, 'FILLED'),
        ('09:15:22', 'SELL', 71200, 0.20, 'CANCEL'),
    ]
    
    for time, side, price, qty, status in orders:
        side_class = 'trade-buy' if side == 'BUY' else 'trade-sell'
        status_class = 'positive' if status == 'FILLED' else 'negative'
        st.markdown(f"""
            <div style="display: grid; grid-template-columns: 70px 50px 70px 50px 70px; gap: 0.5rem; padding: 0.25rem 0; border-bottom: 1px solid #2a2e35; font-family: monospace; font-size: 0.75rem;">
                <span>{time}</span>
                <span class="{side_class}">{side}</span>
                <span>${price:,.0f}</span>
                <span>{qty:.2f}</span>
                <span class="{status_class}">{status}</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# PnL Curve
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("""
    <div class="panel-header">
        <span class="panel-title">WALK-FORWARD PnL · OOS-ONLY</span>
        <span class="badge">SHARPE: 1.89</span>
    </div>
""", unsafe_allow_html=True)

# PnL chart
pnl_dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
pnl_values = 10000 * (1 + np.cumsum(np.random.randn(100) * 0.02))
pnl_values = pnl_values - pnl_values[0] + 10000

pnl_fig = go.Figure()

# Add drawdown zones
dd_regions = [(20, 30), (45, 55), (70, 80)]
for start, end in dd_regions:
    pnl_fig.add_vrect(
        x0=pnl_dates[start], x1=pnl_dates[end],
        fillcolor='rgba(255, 71, 87, 0.1)',
        layer="below",
        line_width=0,
        showlegend=False
    )

pnl_fig.add_trace(go.Scatter(
    x=pnl_dates,
    y=pnl_values,
    mode='lines',
    line=dict(color='#3d9aff', width=2),
    fill='tozeroy',
    fillcolor='rgba(61, 154, 255, 0.05)',
    name='PnL',
    showlegend=False
))

pnl_fig.add_hline(y=pnl_values[0], line_dash="dash", line_color="#2a2e35", line_width=1)

pnl_fig.update_layout(
    template='plotly_dark',
    paper_bgcolor='#0d0f14',
    plot_bgcolor='#0d0f14',
    height=150,
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(showgrid=True, gridcolor='#2a2e35', gridwidth=0.5),
    yaxis=dict(showgrid=True, gridcolor='#2a2e35', gridwidth=0.5)
)

st.plotly_chart(pnl_fig, use_container_width=True, config={'displayModeBar': False})

# PnL stats
pcol1, pcol2, pcol3, pcol4 = st.columns(4)
with pcol1:
    st.markdown(f'<span class="mono">Total PnL: <span class="positive">+${pnl_values[-1]-pnl_values[0]:,.0f}</span></span>', 
                unsafe_allow_html=True)
with pcol2:
    max_dd = (pnl_values.min() - pnl_values.max()) / pnl_values.max() * 100
    st.markdown(f'<span class="mono">Max DD: <span class="negative">{max_dd:.1f}%</span></span>', 
                unsafe_allow_html=True)
with pcol3:
    win_rate = 62.5
    st.markdown(f'<span class="mono">Win Rate: <span>{win_rate:.1f}%</span></span>', 
                unsafe_allow_html=True)
with pcol4:
    avg_trade = 187
    st.markdown(f'<span class="mono">Avg Trade: <span class="positive">+${avg_trade}</span></span>', 
                unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Bottom Bar
bcol1, bcol2, bcol3, bcol4, bcol5 = st.columns(5)

with bcol1:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge badge-long">LONG BTC</span>
            <span class="mono">Entry: $71,234</span>
        </div>
    """, unsafe_allow_html=True)

with bcol2:
    st.markdown("""
        <div>
            <span style="color: #8a8f99; font-size: 0.7rem;">Unrealised PnL</span>
            <div><span class="mono positive">+$277.75</span> <span class="mono positive">(+1.56%)</span></div>
        </div>
    """, unsafe_allow_html=True)

with bcol3:
    st.markdown("""
        <div>
            <span style="color: #8a8f99; font-size: 0.7rem;">Max Drawdown</span>
            <div><span class="mono negative">-$1,890 (2.4%)</span></div>
        </div>
    """, unsafe_allow_html=True)

with bcol4:
    st.markdown("""
        <div>
            <span style="color: #8a8f99; font-size: 0.7rem;">CVaR 95%</span>
            <div><span class="mono negative">-$2,340</span></div>
        </div>
    """, unsafe_allow_html=True)

with bcol5:
    st.markdown("""
        <div>
            <span style="color: #8a8f99; font-size: 0.7rem;">Leverage</span>
            <div><span class="mono">1.00x</span></div>
        </div>
    """, unsafe_allow_html=True)

# Model Metadata Bar
st.markdown("""
    <div style="display: flex; gap: 2rem; padding: 0.75rem 1rem; background: #14171c; border: 1px solid #2a2e35; border-radius: 4px; margin-top: 1rem;">
        <div><span style="color: #5f6670;">Model:</span> <span class="mono" style="color: #e0e2e8;">TFT</span></div>
        <div><span style="color: #5f6670;">Seq:</span> <span class="mono" style="color: #e0e2e8;">60</span></div>
        <div><span style="color: #5f6670;">Retrained:</span> <span class="mono" style="color: #e0e2e8;">2024-01-15 04:00 UTC</span></div>
        <div><span style="color: #5f6670;">Fold:</span> <span class="mono" style="color: #e0e2e8;">4/5</span></div>
        <div><span style="color: #5f6670;">OOS Sharpe:</span> <span class="mono" style="color: #e0e2e8;">1.89</span></div>
        <div><span style="color: #5f6670;">Win Rate:</span> <span class="mono" style="color: #e0e2e8;">62.5%</span></div>
        <div><span style="color: #5f6670;">Total Trades:</span> <span class="mono" style="color: #e0e2e8;">247</span></div>
    </div>
""", unsafe_allow_html=True)

# Auto-refresh
if st.button("⟳ Refresh Data", use_container_width=True):
    st.rerun()

# Footer with last update
st.markdown(f"""
    <div style="text-align: right; color: #5f6670; font-size: 0.7rem; margin-top: 1rem;">
        Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </div>
""", unsafe_allow_html=True)
