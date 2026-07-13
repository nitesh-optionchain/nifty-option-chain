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

# ================= 1. PAGE CONFIGURATION & THEME =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Terminal")

# 🔄 5-Second Safe Counter to push stream memory changes onto Plotly canvas
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

# 📂 BACKUP SYSTEM DIRECTORY ROUTING
BACKUP_DIR = "chart_backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Master Local State Caching Initialization
if "websocket_ohlcv_buffer" not in st.session_state:
    st.session_state.websocket_ohlcv_buffer = {}

# ==============================================================================
# 🎯 2. SIDEBAR CONTROLS LAYOUT
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

st.sidebar.header("⚙️ Assets & Settings")
target_symbol = st.sidebar.selectbox("🔤 Select Asset", ["NIFTY", "SENSEX", "HDFCBANK"], index=0)

st.sidebar.header("📊 Indicators Visibility")
show_zones = st.sidebar.checkbox("🎯 Show Next Day Zones (DR/DS Boxes)", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=True)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=True)
show_daily_camarilla = st.sidebar.checkbox("📅 Show Daily Camarilla Pivots", value=False)
show_monthly_camarilla = st.sidebar.checkbox("🌙 Show Monthly Camarilla Pivots", value=False)

st.sidebar.header("🛠️ Indicator Settings")
rsi_period = int(st.sidebar.number_input("RSI Period", min_value=2, max_value=50, value=14))
st_multiplier = float(st.sidebar.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1))
st_period = int(st.sidebar.number_input("SuperTrend ATR Period", min_value=1, max_value=50, value=10))

st.sidebar.header("🎨 Customize Line Colors")
with st.sidebar.expander("Change Line Colors"):
    st_color = st.color_picker("SuperTrend Line Color", "#f97316")
    dma9_color = st.color_picker("9 DMA Color", "#ffeb3b")
    dma20_color = st.color_picker("20 DMA Color", "#00e5ff")
    dma50_color = st.color_picker("50 DMA Color", "#e040fb")
    vwap_color = st.color_picker("VWAP Color", "#00f0ff")

st.sidebar.header("✏️ Custom Drawing Tools")
with st.sidebar.expander("Draw Manual Lines"):
    draw_h_line = st.checkbox("Enable Horizontal Line")
    h_line_value = st.number_input("Horizontal Price Value", value=0.0)
    h_line_color = st.color_picker("Horizontal Line Color", "#ffffff")
    
    draw_v_line = st.checkbox("Enable Vertical Line")
    v_line_idx = st.number_input("Vertical Line Candle Offset", min_value=1, max_value=100, value=5)
    v_line_color = st.color_picker("Vertical Line Color", "#ff00ff")

# 📂 Paths Framework Setup for SDK imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

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
                if sym:
                    # Converting native integer paise units safely to standard float rupees
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    v = float(getattr(msg, 'bucket_volume', 0))
                    
                    if c > 0:
                        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        date_str = datetime.now().strftime("%Y_%m_%d")
                        
                        # --- EXPLICIT AUTO-CSV RECORDER LOGIC ---
                        csv_filename = f"{sym}_10m_{date_str}.csv"
                        full_csv_path = os.path.join(BACKUP_DIR, csv_filename)
                        
                        new_row_df = pd.DataFrame([{
                            "Timestamp": time_str, "open": o, "high": h, "low": l, "close": c, "volume": v
                        }])
                        
                        # Append row cleanly to local file storage disk
                        if not os.path.exists(full_csv_path):
                            new_row_df.to_csv(full_csv_path, index=False)
                        else:
                            new_row_df.to_csv(full_csv_path, mode='a', header=False, index=False)
                        
                        # Store in dynamic session buffer framework memory
                        if sym not in st.session_state.websocket_ohlcv_buffer:
                            st.session_state.websocket_ohlcv_buffer[sym] = []
                        
                        buf = st.session_state.websocket_ohlcv_buffer[sym]
                        if len(buf) > 0 and buf[-1]["time"] == time_str:
                            buf[-1].update({"high": max(buf[-1]["high"], h), "low": min(buf[-1]["low"], l), "close": c, "volume": buf[-1]["volume"] + v})
                        else:
                            buf.append({"time": time_str, "open": o, "high": h, "low": l, "close": c, "volume": v})
                            
                        if len(buf) > 300:
                            buf.pop(0)
            except Exception as thread_err:
                print(f"Streaming write validation fail: {thread_err}")

        socket = websocketdata.NubraDataSocket(
            client=nubra_client,
            on_ohlcv_data=on_ohlcv_data,
            on_connect=lambda m: print("[Socket Status: LIVE_CONNECTED]"),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}")
        )
        
        socket.connect()
        socket.subscribe(["NIFTY", "HDFCBANK"], data_type="ohlcv", interval="10m", exchange="NSE")
        socket.subscribe(["SENSEX"], data_type="ohlcv", interval="10m", exchange="BSE")
        return socket
    except Exception as e:
        print(f"Socket initialization fail: {e}")
        return None

active_socket = initialize_live_ohlcv_stream()

# ==============================================================================
# 🧠 4. MATHEMATICAL INDICATORS COMPUTATION ENGINE
# ==============================================================================
def calculate_indicators(df, mult_value, period_value, rsi_pd_value):
    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    
    # 💧 Safe Intra-day VWAP
    if 'volume' in df.columns:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        pv = typical_price * df['volume'].fillna(0)
        df['vwap'] = pv.cumsum() / (df['volume'].fillna(0).cumsum() + 1e-10)
    else:
        df['vwap'] = df['close']
        
    # ⚡ SuperTrend Engine
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['close'].shift(1)).abs()
    df['tr3'] = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period_value, min_periods=1).mean()
    df['hl2'] = (df['high'] + df['low']) / 2
    df['upper_band'] = df['hl2'] + (mult_value * df['atr'])
    df['lower_band'] = df['hl2'] - (mult_value * df['atr'])
    
    df['supertrend'] = np.nan
    df['trend'] = 1
    df.iloc[0, df.columns.get_loc('supertrend')] = df['lower_band'].iloc[0]
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['upper_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = 1
        elif df['close'].iloc[i] < df['lower_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = -1
        else: df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
            
        if df['trend'].iloc[i] == 1: df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
        else: df.loc[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
    df['supertrend'] = df['supertrend'].ffill()

    # Camarilla Pivots Engine
    df['daily_H4'] = df['close'] + ((df['high'] - df['low']) * 1.1 / 2)
    df['daily_H3'] = df['close'] + ((df['high'] - df['low']) * 1.1 / 4)
    df['daily_L3'] = df['close'] - ((df['high'] - df['low']) * 1.1 / 4)
    df['daily_L4'] = df['close'] - ((df['high'] - df['low']) * 1.1 / 2)
    df['monthly_H4'] = df['daily_H4']
    df['monthly_H3'] = df['daily_H3']
    df['monthly_L3'] = df['daily_L3']
    df['monthly_L4'] = df['daily_L4']
    return df

# ==============================================================================
# 🧠 5. HYBRID LOADING PIPELINE (Live vs Past File Offline Link Switch)
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
    # Read active memory buffer array values if stream data is present
    buf = st.session_state.websocket_ohlcv_buffer.get(target_symbol, [])
    if len(buf) > 0:
        df = pd.DataFrame(buf)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    else:
        # Emergency Safe Baseline Seeder to keep Plotly framework active
        st.info(f"⏳ Waiting for the first live stream tick for {target_symbol}... (Please refresh in seconds)")
        mock_time = datetime.now()
        data = {"open": [24150.0], "high": [24180.0], "low": [24120.0], "close": [24160.0], "volume": [100.0]}
        df = pd.DataFrame(data, index=[mock_time])

df = calculate_indicators(df, st_multiplier, st_period, rsi_period)
latest_row = df.iloc[-1]
current_ltp = float(latest_row['close'])

# ==============================================================================
# 👑 6. ACCURATE RATIO PRECISE ZONES
# ==============================================================================
if target_symbol == "NIFTY":
    base_upper = float(((current_ltp + 25) // 50) * 50 + 50)
    sup_low, sup_high = base_upper, float(base_upper + 30)
    base_lower = float(((current_ltp - 25) // 50) * 50 - 50)
    dem_low, dem_high = base_lower, float(base_lower + 30)
else:
    sup_high, sup_low = float(current_ltp * 1.015), float(current_ltp * 1.010)
    dem_high, dem_low = float(current_ltp * 0.990), float(current_ltp * 0.985)

p_point = round((sup_low + dem_high + current_ltp) / 3)

# 🌟 HTML PANEL HEADER RENDERING
status_title = f"📁 OFFLINE FILE VIEW: {selected_backup_file}" if is_backup_loaded_flag else f"⚡ {target_symbol} REAL-TIME TERMINAL"
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
# 🖥️ 7. ORIGINAL PLOTLY SINGLE SUBPLOT DESIGN
# ==============================================================================
fig = make_subplots(rows=1, cols=1)

fig.add_trace(gr.Candlestick(
    x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price Candle",
    increasing_line_color='#00cc66', decreasing_line_color='#ff3333',
    increasing_fillcolor='#00cc66', decreasing_fillcolor='#ff3333'
), row=1, col=1)

if show_zones:
    box_start_idx = max(0, len(df) - 15)
    fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=sup_low, y1=sup_high, fillcolor="rgba(239, 68, 68, 0.20)", line=dict(color="#ff3333", width=2))
    fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=dem_low, y1=dem_high, fillcolor="rgba(16, 185, 129, 0.20)", line=dict(color="#00cc66", width=2))

fig.add_hline(y=p_point, line_width=1.5, line_dash="dashdot", line_color="#eab308", annotation_text=f"PP: {p_point}", annotation_position="top left")

if show_supertrend:
    fig.add_trace(gr.Scatter(x=df.index, y=df['supertrend'], line=dict(color=st_color, width=2), name="SuperTrend"))
if show_dma:
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"))
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"))
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"))
if show_vwap and 'vwap' in df.columns:
    fig.add_trace(gr.Scatter(x=df.index, y=df['vwap'], line=dict(color=vwap_color, width=3.5), name="VWAP"))

if show_daily_camarilla:
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H4'], line=dict(color='#ff1744', width=1, dash="dot"), name="Daily H4"))
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L3'], line=dict(color='#00e676', width=1, dash="dot"), name="Daily L3"))

if draw_h_line and h_line_value > 0:
    fig.add_hline(y=h_line_value, line_color=h_line_color, line_width=2, annotation_text=f"Level: {h_line_value:.2f}")
if draw_v_line and len(df) > v_line_idx:
    fig.add_vline(x=df.index[-v_line_idx], line_color=v_line_color, line_width=2, line_dash="dash")

fig.add_trace(gr.Scatter(
    x=[df.index[-1]], y=[current_ltp], mode="markers+text", marker=dict(color="#ffff00", size=10, symbol="arrow-left"),
    text=[f"  ◄ LTP: {current_ltp:.2f}"], textposition="middle right", textfont=dict(color="#ffff00", size=13, family="Arial Black"), showlegend=False
))

# Dynamic Spectrum Auto Axis Scaling
min_price, max_price = float(df['low'].min()), float(df['high'].max())
top_y_limit = max(max_price, sup_high) * 1.005
bottom_y_limit = min(min_price, dem_low) * 0.995

fig.update_layout(
    height=720, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=15, r=150, t=10, b=30),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[bottom_y_limit, top_y_limit], autorange=False, fixedrange=False),
    xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), autorange=True, fixedrange=False),
    paper_bgcolor='#030712', plot_bgcolor='#030712'
)
st.plotly_chart(fig, use_container_width=True)

# Bottom Info Metrics
c1, c2, c3 = st.columns(3)
with c1: st.info(f"🔴 **Resistance Zone (DR):** {sup_low:.1f} - {sup_high:.1f}")
with c2: st.success(f"🟢 **Support Zone (DS):** {dem_low:.1f} - {dem_high:.1f}")
with c3: st.warning(f"🟡 **Terminal Candle LTP:** ₹{current_ltp:.2f}")
