import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as gr
from plotly.subplots import make_subplots

# ==============================================================================
# 🎯 1. PREMIUM TERMINAL CONFIGURATION & LAYOUT ENGINE
# ==============================================================================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Terminal")

# 🌟 PREMIUM DARK THEME STYLE SHEET INJECTION
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        .tc-dashboard-header {
            background: linear-gradient(135deg, #111827 0%, #030712 100%);
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 14px 20px;
            margin-bottom: 18px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }
        .tc-title {
            color: #f3f4f6;
            font-size: 20px;
            font-weight: 800;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .tc-metrics-container {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .tc-badge {
            padding: 6px 14px;
            border-radius: 5px;
            font-size: 13px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
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

# 📂 Path Routing Plugs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# ==============================================================================
# 🎯 2. SIDEBAR CONTROLS LAYOUT (Includes Systematic Timeframes)
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
target_symbol = st.sidebar.selectbox("🔤 Select Asset", ["NIFTY", "SENSEX"], index=0)

# ✅ TIMEFRAME FIX MAP: Directly linked mapping logic to inject down into historical engine
timeframe_mapping = {
    "1 Minute": "1m",
    "5 Minutes": "5m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "Daily": "1d"
}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Active Timeframe", list(timeframe_mapping.keys()), index=1)
interval = timeframe_mapping[selected_tf_label]

st.sidebar.header("📊 Indicators Visibility")
show_zones = st.sidebar.checkbox("🎯 Show Next Day Zones (DR/DS Boxes)", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=True)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=True)
show_daily_camarilla = st.sidebar.checkbox("📅 Show Daily Camarilla Pivots", value=False)

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

# ==============================================================================
# 🔐 3. GLOBAL CACHED CONNECTION ENGINE (Strict Anti-Collision Handler)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_cached_nubra_engine():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as network_error:
        print(f"Master Connection Token Lock Mismatch: {network_error}")
        return None

market_engine = initialize_cached_nubra_engine()

# ==============================================================================
# 🧠 4. MATHEMATICAL INDICATORS COMPUTATION ENGINE
# ==============================================================================
def calculate_indicators(df, mult_value, period_value, rsi_pd_value):
    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    
    if 'volume' in df.columns:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        pv = typical_price * df['volume'].fillna(0)
        df['vwap'] = pv.cumsum() / (df['volume'].fillna(0).cumsum() + 1e-10)
    else:
        df['vwap'] = df['close']
        
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

    df['daily_H4'] = df['close'] + ((df['high'] - df['low']) * 1.1 / 2)
    df['daily_H3'] = df['close'] + ((df['high'] - df['low']) * 1.1 / 4)
    df['daily_L3'] = df['close'] - ((df['high'] - df['low']) * 1.1 / 4)
    df['daily_L4'] = df['close'] - ((df['high'] - df['low']) * 1.1 / 2)
    return df

# ==============================================================================
# 🧠 5. HYBRID STABLE LOADING PIPELINE (Live Query Mapped to Offline Local CSV)
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

if df is None and market_engine:
    try:
        # Requesting safe short historical block windows
        end_dt = datetime.utcnow()
        lookback_days = 20 if interval == "1d" else 3
        start_dt = end_dt - timedelta(days=lookback_days)
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        ex_type = "BSE" if target_symbol == "SENSEX" else "NSE"
        
        # Pull snapshot current price snapshot matrix
        snap = market_engine.current_price(target_symbol, exchange=ex_type)
        
        # Mapped REST History Extractor using documented parameters explicitly
        res = market_engine.historical_data({
            "exchange": ex_type, "type": "INDEX", "values": [target_symbol],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_str, "endDate": end_str, "interval": interval,  # ✅ Timeframe Bound Injector Map
            "intraDay": True if interval != "1d" else False, "realTime": False
        })
        
        if res and hasattr(res, 'result') and res.result and len(res.result) > 0:
            for inst_dict in res.result[0].values:
                stock_chart = inst_dict.get(target_symbol) if isinstance(inst_dict, dict) else getattr(inst_dict, target_symbol, None)
                
                if stock_chart and hasattr(stock_chart, 'close') and stock_chart.close:
                    history_list = []
                    total_ticks = len(stock_chart.close)
                    
                    for i in range(total_ticks):
                        # Extract matching precise inner values from TimeSeriesPoint structures safely
                        o = float(stock_chart.open[i].value) / 100.0
                        h = float(stock_chart.high[i].value) / 100.0
                        l = float(stock_chart.low[i].value) / 100.0
                        c = float(stock_chart.close[i].value) / 100.0
                        
                        mins_gap = 5 if interval == "5m" else 15 if interval == "15m" else 30 if interval == "30m" else 60 if interval == "1h" else 1
                        base_time = datetime.now() - timedelta(minutes=mins_gap * (total_ticks - i)) if interval != "1d" else datetime.now() - timedelta(days=(total_ticks - i))
                        stamp_str = base_time.strftime("%Y-%m-%d %H:%M:%S") if interval != "1d" else base_time.strftime("%Y-%m-%d")
                        
                        history_list.append({
                            "Timestamp": stamp_str, "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                        })
                    
                    df = pd.DataFrame(history_list)
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    df.set_index('Timestamp', inplace=True)
                    
                    # ✅ AUTOMATIC AUTO-SAVE DAILY FILE LINK SYSTEM
                    file_date = datetime.now().strftime("%Y_%m_%d")
                    csv_name = f"{target_symbol}_{interval}_{file_date}.csv"
                    full_csv_path = os.path.join(BACKUP_DIR, csv_name)
                    df.to_csv(full_csv_path)
    except Exception as e:
        print(f"Extraction Pipeline Fail trace log: {e}")

if df is None or df.empty:
    st.info(f"⏳ Waiting for stable historical block matrix for {target_symbol}. Showing placeholder grid...")
    mock_time = datetime.now()
    df = pd.DataFrame({"open": [24150.0], "high": [24180.0], "low": [24120.0], "close": [24160.0], "volume": [100.0]}, index=[mock_time])

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
status_title = f"📁 OFFLINE CSV FILE VIEW: {selected_backup_file}" if is_backup_loaded_flag else f"⚡ {target_symbol} ({selected_tf_label}) REAL-TIME TERMINAL"
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
# 🖥️ 7. ORIGINAL PLOTLY HIGH-SPEED CANVAS DESIGN
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

# Render interactive chart
st.plotly_chart(fig, use_container_width=True)

# Manual Reload Hook Link
if st.button("🔄 Force Reload Historical Core"):
    st.cache_resource.clear()
    st.rerun()
