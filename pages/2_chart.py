import sys
import os
import time
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 📊 Wide mode configuration
st.set_page_config(layout="wide", page_title="SmartWealth Live Chart Terminal")

# Anti-Crash Module
import pandas as pd

# 🔄 2-SECOND REALTIME PIPELINE SYNCHRONIZER
st_autorefresh(interval=2000, key="clean_direct_stream_bridge")

# ==============================================================================
# 🔌 NUBRA SDK BROKER CONNECTION
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
# 🎛️ SIDEBAR SELECTIONS (Bina Kisi Login Gateway Ke)
# ==============================================================================
st.sidebar.markdown("### 📊 Chart Configuration")
selected_index_target = st.sidebar.selectbox("Select Target Index", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Matrix", ["5m", "10m", "15m", "30m", "1d"], index=0)

times, opens, highs, lows, closes = [], [], [], [], []
live_price = 0.0
live_change = 0.0
is_market_open = False

if market_engine:
    try:
        symbol_name = "Nifty 50" if selected_index_target == "NIFTY" else "SENSEX"
        exch_name = "NSE" if selected_index_target == "NIFTY" else "BSE"
        
        # Pull Historical Data for baseline candles grid
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

        # Map WebSocket live response variables
        snap = market_engine.current_price(selected_index_target, exchange=exch_name)
        if snap:
            raw_val = getattr(snap, 'index_value', getattr(snap, 'price', None))
            raw_chg = getattr(snap, 'changepercent', getattr(snap, 'change', 0.0))
            
            if raw_val:
                live_price = float(raw_val) / 100
                live_change = float(raw_chg)
                is_market_open = True
                
                if len(closes) > 0:
                    closes[-1] = live_price
                    if live_price > highs[-1]: highs[-1] = live_price
                    if live_price < lows[-1]: lows[-1] = live_price
                    
    except Exception as e:
        st.sidebar.error(f"Data Fetch Notice: {str(e)}")

# If market is closed or API response lags, use fallback from last available candles
if not closes:
    st.error("⚠️ Data link offline. Connecting to broker repository...")
    st.stop()

if not is_market_open:
    live_price = closes[-1]
    if len(closes) > 1:
        live_change = ((closes[-1] - closes[-2]) / closes[-2]) * 100

# ==============================================================================
# 📈 PHASE 2: LIVE UP/DOWN INDEX HEADER INTERFACE
# ==============================================================================
h_col1, h_col2 = st.columns([4, 4])
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
    status_tag = "🟢 Market Open" if is_market_open else "🔴 Market Closed"
    st.markdown(f"<div style='text-align:right;padding-top:15px;'><b>Engine Status:</b> {status_tag} | <b>Interval:</b> {selected_tf}</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🖥️ PHASE 3: STRICT RED & GREEN CANDLESTICK GRAPH
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
    xaxis=dict(showgrid=True, gridcolor="#1e293b"),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b")
)

st.plotly_chart(fig, use_container_width=True)
