import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 📊 Wide mode terminal configuration
st.set_page_config(layout="wide", page_title="SmartWealth Live Terminal")

# Anti-Crash Module
import pandas as pd

# ==============================================================================
# 🗄️ 1. PERMANENT SQLITE USER SECURITY ENGINE
# ==============================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_management.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, created_at) VALUES ('admin', 'Admin Chief', ?)", (str(datetime.now()),))
    conn.commit()
    conn.close()

init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Security Validation Interface
if not st.session_state.authenticated:
    st.sidebar.subheader("🔒 Terminal Access Controller")
    login_id = st.sidebar.text_input("User ID Key", type="password")
    if st.sidebar.button("Verify Authentication", use_container_width=True):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (login_id,))
        user_row = cursor.fetchone()
        conn.close()
        if user_row:
            st.session_state.authenticated = True
            st.session_state.current_user = user_row[0]
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid Access Key.")
    st.stop()

# 🔄 2-SECOND REALTIME PIPELINE SYNCHRONIZER
st_autorefresh(interval=2000, key="realtime_nubra_stream_bridge")

# ==============================================================================
# 🔌 2. SDK BROKER WEBSOCKET DATA STREAM INTEGRATION
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

@st.cache_resource(show_spinner=False)
def connect_broker_pipeline():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception:
        return None

market_engine = connect_broker_pipeline()

# ==============================================================================
# 🎛️ SIDEBAR SELECTIONS
# ==============================================================================
st.sidebar.markdown(f"### 👤 Active: {st.session_state.current_user}")
if st.sidebar.button("🔒 Secure Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

selected_index_target = st.sidebar.selectbox("Select Target Index", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Matrix", ["5m", "10m", "15m", "30m", "1d"], index=0)

# ==============================================================================
# 🧠 3. HISTORICAL ENGINE AND REALTIME DICTIONARY PARSER
# ==============================================================================
times, opens, highs, lows, closes = [], [], [], [], []
live_price = 0.0
live_change = 0.0
is_market_open = False

if market_engine:
    try:
        symbol_name = "Nifty 50" if selected_index_target == "NIFTY" else "SENSEX"
        exch_name = "NSE" if selected_index_target == "NIFTY" else "BSE"
        
        # A. Pull strictly HISTORICAL array for baseline candles grid
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=3)
        
        hist_response = market_engine.historical_data({
            "exchange": exch_name,
            "type": "INDEX",
            "values": [symbol_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": selected_tf,
            "intraDay": True,
            "realTime": False
        })
        
        if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
            for candle in hist_response.candles:
                times.append(getattr(candle, 'timestamp', ''))
                opens.append(float(getattr(candle, 'open', 0)) / 100)
                highs.append(float(getattr(candle, 'high', 0)) / 100)
                lows.append(float(getattr(candle, 'low', 0)) / 100)
                closes.append(float(getattr(candle, 'close', 0)) / 100)

        # B. Map WebSocket live response variables strictly from user docs format
        snap = market_engine.current_price(selected_index_target, exchange=exch_name)
        if snap:
            raw_val = getattr(snap, 'index_value', getattr(snap, 'price', None))
            raw_chg = getattr(snap, 'changepercent', getattr(snap, 'change', 0.0))
            
            if raw_val:
                live_price = float(raw_val) / 100
                live_change = float(raw_chg)
                is_market_open = True
                
                # Append live price node directly to update the active ongoing candle stream
                if len(closes) > 0:
                    closes[-1] = live_price
                    if live_price > highs[-1]: highs[-1] = live_price
                    if live_price < lows[-1]: lows[-1] = live_price
                    
    except Exception as e:
        st.sidebar.error(f"Stream Status: {str(e)}")

# Safe check: If no data at all (neither historical nor live)
if not closes:
    st.error("⚠️ Data connection failed. Please check your Nubra SDK API status.")
    st.stop()

# If market is closed, use the last historical close price for display header
if not is_market_open:
    live_price = closes[-1]
    # Calculate difference percentage between last two candles for header look
    if len(closes) > 1:
        live_change = ((closes[-1] - closes[-2]) / closes[-2]) * 100

# ==============================================================================
# 📈 PHASE 4: LIVE TOP HEADER UI (GREEN / RED DYNAMIC INDICATORS)
# ==============================================================================
h_col1, h_col2, h_col3 = st.columns([2, 2, 4])
with h_col1:
    delta_str = f"{live_change:+.2f}%"
    label_status = "REALTIME SPOT" if is_market_open else "LAST CLOSED PRICE"
    st.metric(
        label=f"📈 {selected_index_target} {label_status}", 
        value=f"{live_price:,.2f}", 
        delta=delta_str, 
        delta_color="normal" if live_change >= 0 else "inverse"
    )
with h_col2:
    st.write(f"**Asset Node:** {selected_index_target} | **Interval:** {selected_tf}")
    if is_market_open:
        st.caption("🟢 Market is OPEN - Streaming Live Ticks")
    else:
        st.caption("🔴 Market is CLOSED - Showing Historical Base Candles")
with h_col3:
    st.markdown(f"<div style='text-align:right;color:#64748b;padding-top:10px;'>👤 User Connected: <b>{st.session_state.current_user}</b></div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🖥️ PHASE 5: REAL GREEN & RED CANDLESTICK TERMINAL
# ==============================================================================
fig = go.Figure(data=[go.Candlestick(
    x=times, open=opens, high=highs, low=lows, close=closes,
    increasing_line_color='#22c55e', decreasing_line_color='#ef4444', 
    increasing_fillcolor='#22c55e', decreasing_fillcolor='#ef4444', 
    name=selected_index_target
)])

fig.update_layout(
    height=620, xaxis_rangeslider_visible=False, template="plotly_dark",
    paper_bgcolor='#030712', plot_bgcolor='#030712',
    margin=dict(l=15, r=70, t=10, b=30),
    xaxis=dict(showgrid=True, gridcolor="#1e293b", linewidth=1, linecolor='#334155'),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", linewidth=1, linecolor='#334155')
)

st.plotly_chart(fig, use_container_width=True)
