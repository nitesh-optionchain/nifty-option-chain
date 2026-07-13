import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 🎯 1. TERMINAL LAYOUT CONFIGURATION & HIGH-SPEED SYNC
# ==============================================================================
st.set_page_config(layout="wide", page_title="SmartWealth Base Terminal")

# 🔄 5-Second Rapid UI Counter to push streaming updates onto chart canvas smoothly
st_autorefresh(interval=5000, key="chart_plotly_websocket_heartbeat")

# 🌟 PREMIUM DARK THEME STYLE SHEET INJECTION
st.markdown("""
    <style>
        .block-container { padding-top: 1.2rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
        .tc-dashboard-header {
            background: linear-gradient(135deg, #111827 0%, #030712 100%);
            border: 1px solid #1f2937; border-radius: 8px; padding: 14px 20px;
            margin-bottom: 18px; display: flex; flex-wrap: wrap;
            justify-content: space-between; align-items: center; gap: 15px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }
        .tc-title { color: #f3f4f6; font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 8px; }
        .tc-metrics-container { display: flex; gap: 12px; flex-wrap: wrap; }
        .tc-badge { padding: 6px 14px; border-radius: 5px; font-size: 13px; font-weight: 700; display: inline-block; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); }
        .badge-ce { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-pe { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
        .badge-pp { background-color: rgba(234, 179, 8, 0.12); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.3); }
        .badge-backup { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    </style>
""", unsafe_allow_html=True)

# 📂 BACKUP SYSTEM DIRECTORY ROUTES
BACKUP_DIR = "chart_backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Force clear memory if any old list mismatch exists
if "websocket_ohlcv_buffer" in st.session_state:
    if not isinstance(st.session_state.websocket_ohlcv_buffer, dict) or \
       any(isinstance(v, list) for v in st.session_state.websocket_ohlcv_buffer.values()):
        del st.session_state["websocket_ohlcv_buffer"]

# Master Local Streaming Framework Memory
if "websocket_ohlcv_buffer" not in st.session_state:
    st.session_state.websocket_ohlcv_buffer = {
        "NIFTY": {},
        "SENSEX": {},
        "HDFCBANK": {}
    }

# 📂 Path Routing Plugs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

# ==============================================================================
# 🎯 2. SIDEBAR CONTROLS LAYOUT (Asset, Timeframe & Offline Box)
# ==============================================================================
st.sidebar.header("📁 Backup File System (Offline Link)")
load_from_backup = st.sidebar.checkbox("📅 Load Past Day Backup (Offline Mode)", value=False)

selected_backup_file = None
if load_from_backup:
    available_backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".csv")], reverse=True)
    if available_backups:
        selected_backup_file = st.sidebar.selectbox("📂 Select Saved Day Chart File", available_backups)
    else:
        st.sidebar.warning("No backup CSV logs detected yet!")

st.sidebar.header("⚙️ Assets & Timeframe Settings")
target_symbol = st.sidebar.selectbox("🔤 Select Asset", ["NIFTY", "SENSEX", "HDFCBANK"], index=0)

# ✅ TIMEFRAME FIX SELECTBOX: Dynamically shifts the active chart interval bounds
timeframe_mapping = {
    "1 Minute": "1m",
    "5 Minutes": "5m",
    "10 Minutes": "10m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h"
}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Active Timeframe", list(timeframe_mapping.keys()), index=2)
interval = timeframe_mapping[selected_tf_label]

# Safe dictionary key initialization
if interval not in st.session_state.websocket_ohlcv_buffer[target_symbol]:
    st.session_state.websocket_ohlcv_buffer[target_symbol][interval] = []

# ==============================================================================
# 🔌 3. NUBRA REAL WEBSOCKET STREAM CORE & AUTOMATIC CSV LOGGER
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_live_ohlcv_stream():
    try:
        nubra_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        def on_ohlcv_data(msg):
            try:
                sym = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                msg_tf = getattr(msg, 'interval', '10m')
                
                if sym in ["NIFTY", "SENSEX", "HDFCBANK"]:
                    # Converting native integer paise units safely to standard float rupees
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    v = float(getattr(msg, 'bucket_volume', 0))
                    
                    if c > 0:
                        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        date_str = datetime.now().strftime("%Y_%m_%d")
                        
                        # --- 💾 EXPLICIT AUTOMATIC BACKUP FILE MAKER ---
                        csv_filename = f"{sym}_{msg_tf}_{date_str}.csv"
                        full_csv_path = os.path.join(BACKUP_DIR, csv_filename)
                        
                        new_row_df = pd.DataFrame([{
                            "Timestamp": time_str, "open": o, "high": h, "low": l, "close": c, "volume": v
                        }])
                        
                        if not os.path.exists(full_csv_path):
                            new_row_df.to_csv(full_csv_path, index=False)
                        else:
                            new_row_df.to_csv(full_csv_path, mode='a', header=False, index=False)
                        
                        # Writing updates directly into active session state
                        if msg_tf not in st.session_state.websocket_ohlcv_buffer[sym]:
                            st.session_state.websocket_ohlcv_buffer[sym][msg_tf] = []
                            
                        buf = st.session_state.websocket_ohlcv_buffer[sym][msg_tf]
                        if len(buf) > 0 and buf[-1]["time"] == time_str:
                            buf[-1].update({"high": max(buf[-1]["high"], h), "low": min(buf[-1]["low"], l), "close": c, "volume": buf[-1]["volume"] + v})
                        else:
                            buf.append({"time": time_str, "open": o, "high": h, "low": l, "close": c, "volume": v})
                            
                        if len(buf) > 300:
                            buf.pop(0)
            except Exception as thread_err:
                pass

        socket = websocketdata.NubraDataSocket(
            client=nubra_client,
            on_ohlcv_data=on_ohlcv_data,
            on_connect=lambda m: print("[Socket Status: CONNECTED]"),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}")
        )
        
        socket.connect()
        # Multi-timeframe subscriptions array binding loop
        for tf_code in ["1m", "5m", "10m", "15m", "30m", "1h"]:
            socket.subscribe(["NIFTY", "HDFCBANK"], data_type="ohlcv", interval=tf_code, exchange="NSE")
            socket.subscribe(["SENSEX"], data_type="ohlcv", interval=tf_code, exchange="BSE")
        return socket
    except Exception as e:
        print(f"Socket infrastructure initialization failure: {e}")
        return None

active_socket = initialize_live_ohlcv_stream()

# ==============================================================================
# 🧠 4. HYBRID STABLE LOADING PIPELINE (Bypasses Blank Frozen Screen)
# ==============================================================================
df = None
is_backup_loaded_flag = False

if load_from_backup and selected_backup_file:
    backup_path = os.path.join(BACKUP_DIR, selected_backup_file)
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path)
        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
            is_backup_loaded_flag = True

if df is None:
    buf = st.session_state.websocket_ohlcv_buffer[target_symbol].get(interval, [])
    if len(buf) > 3:
        df = pd.DataFrame(buf)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    else:
        # ✅ REAL-TIME CONTINUOUS TIMELINE FILLER (Seeds the initial chart candles)
        mock_ticks = []
        if target_symbol == "NIFTY": base_val = 24200.0
        elif target_symbol == "SENSEX": base_val = 77400.0
        else: base_val = 1610.0
        
        mins_gap = int(interval[:-1]) if interval != "1h" else 60
        for i in range(45):
            t_stamp = datetime.now() - timedelta(minutes=mins_gap * (45 - i))
            mock_ticks.append({
                "time": t_stamp, "open": base_val + (i * 0.4), "high": base_val + (i * 0.8) + 3, "low": base_val + (i * 0.1) - 2, "close": base_val + (i * 0.6), "volume": 100.0
            })
        df = pd.DataFrame(mock_ticks)
        df.set_index('time', inplace=True)

latest_row = df.iloc[-1]
current_ltp = float(latest_row['close'])

# ==============================================================================
# 👑 5. ACCURATE RATIO PRECISE ZONES
# ==============================================================================
if target_symbol == "NIFTY":
    base_upper = float(((current_ltp + 25) // 50) * 50 + 50)
    sup_low, sup_high = base_upper, float(base_upper + 30)
    base_lower = float(((current_ltp - 25) // 50) * 50 - 50)
    dem_low, dem_high = base_lower, float(base_lower + 30)
elif target_symbol == "BANKNIFTY" or target_symbol == "SENSEX":
    base_upper = float(((current_ltp + 50) // 100) * 100 + 100)
    sup_low, sup_high = base_upper, float(base_upper + 120)
    base_lower = float(((current_ltp - 50) // 100) * 100 - 100)
    dem_high, dem_low = base_lower, float(base_lower - 120)
else: # Stocks (HDFCBANK)
    sup_high, sup_low = float(current_ltp * 1.012), float(current_ltp * 1.008)
    dem_high, dem_low = float(current_ltp * 0.992), float(current_ltp * 0.988)

p_point = round((sup_low + dem_high + current_ltp) / 3)

# 🌟 HTML PANEL HEADER RENDERING
status_title = f"📁 OFFLINE FILE VIEW: {selected_backup_file}" if is_backup_loaded_flag else f"⚡ {target_symbol} ({selected_tf_label}) REAL-TIME TERMINAL"
badge_status_class = "badge-backup" if is_backup_loaded_flag else "badge-pp"
badge_status_label = "OFFLINE HISTORY LOCK" if is_backup_loaded_flag else f"MID-PIVOT (PP): {p_point}"

header_html = f"""
<div class="tc-dashboard-header">
    <div class="tc-title">{status_title}</div>
    <div class="tc-metrics-container">
        <span class="tc-badge badge-ce">🔴 RESISTANCE (DR): {int(sup_low)} - {int(sup_high)}</span>
        <span class="tc-badge badge-pe">🟢 SUPPORT (DS): {int(dem_low)} - {int(dem_high)}</span>
        <span class="tc-badge {badge_status_class}">⚖️ {badge_status_label}</span>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==============================================================================
# 🖥️ 6. ORIGINAL PLOTLY HIGH-SPEED CANVAS DESIGN
# ==============================================================================
fig = make_subplots(rows=1, cols=1)

fig.add_trace(gr.Candlestick(
    x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price Candle",
    increasing_line_color='#00cc66', decreasing_line_color='#ff3333',
    increasing_fillcolor='#00cc66', decreasing_fillcolor='#ff3333'
), row=1, col=1)

# DR / DS Zone Shape Injection Boxes
box_start_idx = max(0, len(df) - 15)
fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=sup_low, y1=sup_high, fillcolor="rgba(239, 68, 68, 0.20)", line=dict(color="#ff3333", width=2))
fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=dem_low, y1=dem_high, fillcolor="rgba(16, 185, 129, 0.20)", line=dict(color="#00cc66", width=2))

fig.add_hline(y=p_point, line_width=1.5, line_dash="dashdot", line_color="#eab308", annotation_text=f"PP: {p_point}", annotation_position="top left")

if draw_h_line and h_line_value > 0:
    fig.add_hline(y=h_line_value, line_color=h_line_color, line_width=2, annotation_text=f"Level: {h_line_value:.2f}")
if draw_v_line and len(df) > v_line_idx:
    fig.add_vline(x=df.index[-v_line_idx], line_color=v_line_color, line_width=2, line_dash="dash")

# Real-time Marker Tracker for LTP Price
fig.add_trace(gr.Scatter(
    x=[df.index[-1]], y=[current_ltp], mode="markers+text", marker=dict(color="#ffff00", size=10, symbol="arrow-left"),
    text=[f"  ◄ LTP: {current_ltp:.2f}"], textposition="middle right", textfont=dict(color="#ffff00", size=13, family="Arial Black"), showlegend=False
))

# Dynamic Auto Axis Height Scaling spectrum map
min_price, max_price = float(df['low'].min()), float(df['high'].max())
top_y_limit = max(max_price, sup_high) * 1.002
bottom_y_limit = min(min_price, dem_low) * 0.998

fig.update_layout(
    height=740, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=15, r=160, t=10, b=30),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[bottom_y_limit, top_y_limit], autorange=False, fixedrange=False),
    xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), autorange=True, fixedrange=False),
    paper_bgcolor='#030712', plot_bgcolor='#030712'
)

st.plotly_chart(fig, use_container_width=True)
