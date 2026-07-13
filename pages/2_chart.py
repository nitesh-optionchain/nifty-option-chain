import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as gr
from plotly.subplots import make_subplots

# 📊 Wide mode terminal layout configuration
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 📂 Paths Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Secure Environment Keys Bridge
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Master Data Storage Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0.0, "status": "LIVE"},
        "SENSEX": {"price": 0.0, "status": "LIVE"}
    }

# 🔄 Anti-Collision Shared Connection Bridge
market_engine = None
if "global_market_engine" in st.session_state and st.session_state.global_market_engine is not None:
    market_engine = st.session_state.global_market_engine
else:
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        market_engine = MarketData(client)
        st.session_state.global_market_engine = market_engine
    except Exception as e:
        if 'market_engine' in st.session_state:
            market_engine = st.session_state['market_engine']
        elif 'market_data' in st.session_state:
            market_engine = st.session_state['market_data']

# 🔤 Clean Sidebar Menu
target_symbol = st.sidebar.selectbox("🔤 Select Asset", ["NIFTY", "SENSEX"], index=0)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=True)

df = None

# ⚡ DOCUMENTATION CONVERTED DATA FEED PIPELINE
if market_engine:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=7) 
        
        exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
        
        # High speed snapshot fetch
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            st.session_state.master_storage["NIFTY"]["price"] = float(nifty_snap.price) / 100.0
            
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            st.session_state.master_storage["SENSEX"]["price"] = float(sensex_snap.price) / 100.0

        # Historical array parsing using the exact logic from your working script
        response = market_engine.historical_data({
            "exchange": exchange_type,
            "type": "INDEX",
            "values": [target_symbol],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "5m",
            "intraDay": True,
            "realTime": False
        })

        if response and response.result and len(response.result) > 0:
            for instrument_dict in response.result[0].values:
                if target_symbol in instrument_dict:
                    stock_chart = instrument_dict[target_symbol]
                    
                    # Core timezone matching assignment from your backup script
                    timestamps = [pd.to_datetime(p.timestamp, unit="ns", utc=True).tz_convert("Asia/Kolkata") for p in stock_chart.close]
                    
                    data = {
                        "open": [float(p.value / 100.0) for p in stock_chart.open],
                        "high": [float(p.value / 100.0) for p in stock_chart.high],
                        "low": [float(p.value / 100.0) for p in stock_chart.low],
                        "close": [float(p.value / 100.0) for p in stock_chart.close]
                    }
                    df = pd.DataFrame(data, index=timestamps)
                    df.sort_index(inplace=True)
                    
                    # Dynamically calculate indicators
                    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
                    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
                    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
                    
    except Exception as error:
        pass

# ==============================================================================
# 🖥️ CLEAN PLOTLY CANVAS INJECTION
# ==============================================================================
current_ltp = st.session_state.master_storage[target_symbol]["price"]

# Sirf saaf aur clear price header
if current_ltp > 0:
    st.markdown(f"### ₹{current_ltp:,.2f} <span style='font-size:14px; color:#94a3b8;'>({target_symbol} Live LTP)</span>", unsafe_allow_html=True)

if df is not None and not df.empty:
    fig = make_subplots(rows=1, cols=1)

    # Candlesticks Trace
    fig.add_trace(gr.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price",
        increasing_line_color='#00cc66', decreasing_line_color='#ff3333',
        increasing_fillcolor='#00cc66', decreasing_fillcolor='#ff3333'
    ), row=1, col=1)

    # Indicators Trace
    if show_dma:
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_9'], line=dict(color="#ffeb3b", width=1.5), name="9 DMA"), row=1, col=1)
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_20'], line=dict(color="#00e5ff", width=1.5), name="20 DMA"), row=1, col=1)
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_50'], line=dict(color="#e040fb", width=2), name="50 DMA"), row=1, col=1)

    fig.update_layout(
        height=720,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=15, r=10, t=10, b=30),
        yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11)),
        xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11)),
        paper_bgcolor='#030712',
        plot_bgcolor='#030712'
    )
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⏳ Connecting to data feed streams... Please wait.")
