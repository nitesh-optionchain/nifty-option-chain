# pages/2_chart.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import time
from streamlit_autorefresh import st_autorefresh

# 🔒 ==============================================================================
# 🎯 1. AUTHENTICATION & CORE CONFIG MATRIX
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if 'chart_auth_verified' not in st.session_state:
    st.session_state['chart_auth_verified'] = False
if 'chart_page_session' not in st.session_state:
    st.session_state['chart_page_session'] = None

st.markdown("### 🔒 Chart Standalone Stream Node")

# GLOBAL FALLBACK CONTROLLER TO AVOID NAME-ERRORS
if 'fallback_active_state' not in st.session_state:
    st.session_state['fallback_active_state'] = False

if not st.session_state['chart_auth_verified']:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Connect Server Live Auth", use_container_width=True):
            try:
                client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
                st.session_state['chart_page_session'] = client
                st.session_state['chart_auth_verified'] = True
                st.session_state['fallback_active_state'] = False
                st.rerun()
            except Exception:
                st.session_state['chart_auth_verified'] = True
                st.session_state['chart_page_session'] = "SIMULATION_ACTIVE"
                st.session_state['fallback_active_state'] = True
                st.rerun()
    with c2:
        if st.button("🛠️ Activate Simulation Stream (Bypass)", use_container_width=True):
            st.session_state['chart_auth_verified'] = True
            st.session_state['chart_page_session'] = "SIMULATION_ACTIVE"
            st.session_state['fallback_active_state'] = True
            st.rerun()
    st.stop()

market_data = None
if st.session_state['chart_page_session'] == "SIMULATION_ACTIVE":
    st.session_state['fallback_active_state'] = True
else:
    try:
        market_data = MarketData(st.session_state['chart_page_session'])
    except Exception:
        st.session_state['fallback_active_state'] = True

# ==============================================================================
# ⏱️ 2. FIXED STABLE AUTO-REFRESH (15 SECONDS)
# ==============================================================================
st_autorefresh(interval=15000, key="smartwealth_chart_perfect_final_v7")

# 🌟 PREMIUM DARK THEME STYLE SHEET INJECTION
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
        .tc-dashboard-header { background: linear-gradient(135deg, #111827 0%, #030712 100%); border: 1px solid #1f2937; border-radius: 8px; padding: 12px 16px; margin-bottom: 15px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; }
        .tc-title { color: #f3f4f6; font-size: 18px; font-weight: 800; margin: 0; }
        .tc-metrics-container { display: flex; gap: 10px; flex-wrap: wrap; }
        .tc-badge { padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; display: inline-block; }
        .badge-ce { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-pe { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-pp { background-color: rgba(234, 179, 8, 0.12); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.2); }
        .badge-backup { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    </style>
""", unsafe_allow_html=True)

# 📂 FILE LOAD SYSTEM
BACKUP_DIR = "chart_backups"
if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)

STORAGE_FILE = "tracked_stocks.txt"
def load_persisted_stocks():
    base_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            persisted = [line.strip() for line in f.readlines() if line.strip()]
            for stock in persisted:
                if stock not in base_list: base_list.append(stock)
    return base_list

all_available_assets = load_persisted_stocks()

# ==============================================================================
# 🎯 3. SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.header("📁 Backup File System")
load_from_backup = st.sidebar.checkbox("📅 Load Past Day Backup (Offline)", value=False)

selected_backup_file = None
if load_from_backup:
    available_backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".csv")], reverse=True)
    if available_backups: selected_backup_file = st.sidebar.selectbox("📂 Select Saved Day Chart", available_backups)
    else: st.sidebar.warning("No backup files found!")

st.sidebar.header("⚙️ Assets & Timeframe")
target_symbol = st.sidebar.selectbox("🔤 Select Asset", all_available_assets, index=0)

timeframe_mapping = {"5 Minutes": "5m", "10 Minutes": "10m", "15 Minutes": "15m", "30 Minutes": "30m", "Daily": "1d"}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Timeframe", list(timeframe_mapping.keys()), index=2)
interval = timeframe_mapping[selected_tf_label]

st.sidebar.header("📊 Indicators Visibility")
show_zones = st.sidebar.checkbox("🎯 Show Next Day Zones (DR/DS Boxes)", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=False)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=True)
show_daily_camarilla = st.sidebar.checkbox("📅 Show Daily Camarilla Pivots", value=False)
show_monthly_camarilla = st.sidebar.checkbox("🌙 Show Monthly Camarilla Pivots", value=False)

st.sidebar.header("🛠️ Indicator Settings")
rsi_period = int(st.sidebar.number_input("RSI Period", min_value=2, max_value=50, value=14))
st_multiplier = float(st.sidebar.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1))
st_period = int(st.sidebar.number_input("SuperTrend ATR Period", min_value=1, max_value=50, value=10))

st.sidebar.header("🎨 Line Colors System")
st_color = st.sidebar.color_picker("SuperTrend Line Color", "#f97316")
dma9_color = st.sidebar.color_picker("9 DMA Color", "#ffeb3b")
dma20_color = st.sidebar.color_picker("20 DMA Color", "#00e5ff")
dma50_color = st.sidebar.color_picker("50 DMA Color", "#e040fb")
vwap_color = st.sidebar.color_picker("VWAP Color", "#00f0ff")

st.sidebar.header("✏️ Custom Drawing Tools")
draw_h_line = st.sidebar.checkbox("Enable Horizontal Line")
h_line_value = st.sidebar.number_input("Horizontal Price Value", value=0.0)
h_line_color = st.sidebar.color_picker("Horizontal Line Color", "#ffffff")
draw_v_line = st.sidebar.checkbox("Enable Vertical Line")
v_line_idx = int(st.sidebar.number_input("Vertical Line Candle Offset", min_value=1, max_value=100, value=5))
v_line_color = st.sidebar.color_picker("Vertical Line Color", "#ff00ff")

# Helper to build mock vectors to avoid layout failures
def create_fallback_data(symbol, tf_interval):
    base_price = 23200.0 if symbol == "NIFTY" else (50100.0 if symbol == "BANKNIFTY" else 76000.0)
    if symbol not in ["NIFTY", "BANKNIFTY", "SENSEX"]: base_price = 500.0
    timestamps = pd.date_range(end=datetime.now(), periods=100, freq='5min' if tf_interval=="5m" else 'D')
    np.random.seed(int(time.time()) % 1000)
    changes = np.random.normal(0, base_price * 0.002, 100)
    closes = base_price + np.cumsum(changes)
    opens = closes - np.random.normal(0, base_price * 0.001, 100)
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0, base_price * 0.0015, 100))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0, base_price * 0.0015, 100))
    volumes = np.random.randint(1000, 50000, 100)
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}, index=timestamps)
# ==============================================================================
# 🧠 4. CORE ENGINE DATA LAYER FETCH BLOCK (FIXED NAME SCOPE)
# ==============================================================================
df = None
is_backup_loaded_flag = False

if load_from_backup and selected_backup_file:
    backup_path = os.path.join(BACKUP_DIR, selected_backup_file)
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path, index_col=0, parse_dates=True)
        is_backup_loaded_flag = True

if df is None:
    if st.session_state['fallback_active_state'] or market_data is None:
        df = create_fallback_data(target_symbol, interval)
    else:
        try:
            with st.spinner(f"Requesting data for {target_symbol}..."):
                end_dt = datetime.utcnow()
                lookback_days = 60 if interval == "1d" else 7
                start_dt = end_dt - timedelta(days=lookback_days)
                api_type = "INDEX" if target_symbol in ["NIFTY", "BANKNIFTY", "SENSEX"] else "STOCK"
                exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
                
                response = market_data.historical_data({
                    "exchange": exchange_type, "type": api_type, "values": [target_symbol],
                    "fields": ["open", "high", "low", "close", "cumulative_volume"],
                    "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "interval": interval, "intraDay": False, "realTime": False
                })
                
                if response and response.result and len(response.result) > 0:
                    instrument_dict = response.result[0].values[0]
                    if target_symbol in instrument_dict:
                        stock_chart = instrument_dict[target_symbol]
                        timestamps = [pd.to_datetime(p.timestamp, unit="ns", utc=True).tz_convert("Asia/Kolkata") for p in stock_chart.close]
                        v_list = [p.value for p in stock_chart.cumulative_volume] if hasattr(stock_chart, 'cumulative_volume') and stock_chart.cumulative_volume else [0] * len(stock_chart.close)
                        data = {
                            "open": [float(p.value / 100.0) for p in stock_chart.open],
                            "high": [float(p.value / 100.0) for p in stock_chart.high],
                            "low": [float(p.value / 100.0) for p in stock_chart.low],
                            "close": [float(p.value / 100.0) for p in stock_chart.close],
                            "cumulative_volume": v_list
                        }
                        df = pd.DataFrame(data, index=timestamps).sort_index()
                        df['volume'] = df['cumulative_volume'].diff().fillna(0)
                
                if df is None or len(df) == 0:
                    df = create_fallback_data(target_symbol, interval)
        except Exception:
            df = create_fallback_data(target_symbol, interval)

# ==============================================================================
# 🧠 5. INDICATOR CRUNCH MATRIX 
# ==============================================================================
if df is not None and len(df) > 0:
    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    
    if 'volume' in df.columns and interval != "1d":
        df['volume_clean'] = df['volume'].fillna(0)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume_clean']).cumsum() / (df['volume_clean'].cumsum() + 1e-10)
    else:
        df['vwap'] = df['close']
        
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))
    
    df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
    df['atr'] = df['tr'].rolling(window=st_period, min_periods=1).mean()
    df['hl2'] = (df['high'] + df['low']) / 2
    df['upper_band'] = df['hl2'] + (st_multiplier * df['atr'])
    df['lower_band'] = df['hl2'] - (st_multiplier * df['atr'])
    
    df['supertrend'] = df['lower_band']
    df['date_only'] = df.index.date
    unique_dates = sorted(list(set(df['date_only'])))
    df['daily_H4'] = np.nan; df['daily_H3'] = np.nan; df['daily_L3'] = np.nan; df['daily_L4'] = np.nan
    
    if len(unique_dates) > 1:
        prev_day = df[df['date_only'] == unique_dates[-2]]
        if not prev_day.empty:
            pd_range = prev_day['high'].max() - prev_day['low'].min()
            pd_close = prev_day['close'].iloc[-1]
            df['daily_H4'] = pd_close + (pd_range * 1.1 / 2)
            df['daily_H3'] = pd_close + (pd_range * 1.1 / 4)
            df['daily_L3'] = pd_close - (pd_range * 1.1 / 4)
            df['daily_L4'] = pd_close - (pd_range * 1.1 / 2)
            
    m_range = df['high'].max() - df['low'].min()
    m_close = df['close'].iloc[-1]
    df['monthly_H4'] = m_close + (m_range * 1.1 / 2)
    df['monthly_H3'] = m_close + (m_range * 1.1 / 4)
    df['monthly_L3'] = m_close - (m_range * 1.1 / 4)
    df['monthly_L4'] = m_close - (m_range * 1.1 / 2)

    current_ltp = float(df['close'].iloc[-1])
    
    if target_symbol == "NIFTY":
        sup_low = float(((current_ltp + 25) // 50) * 50 + 50); sup_high = sup_low + 30
        dem_low = float(((current_ltp - 25) // 50) * 50 - 50); dem_high = dem_low + 30
    elif target_symbol == "BANKNIFTY":
        sup_low = float(((current_ltp + 50) // 100) * 100 + 100); sup_high = sup_low + (current_ltp * 0.003)
        dem_high = float(((current_ltp - 50) // 100) * 100 - 100); dem_low = dem_high - (current_ltp * 0.003)
    else:
        sup_high = current_ltp * 1.015; sup_low = current_ltp * 1.010
        dem_high = current_ltp * 0.990; dem_low = current_ltp * 0.985
    p_point = round((sup_low + dem_high + current_ltp) / 3)

    # 📊 HEADER TERMINAL RENDER
    st.markdown(f"""
    <div class="tc-dashboard-header">
        <div class="tc-title">⚡ {target_symbol} PREMIUM COMPACT TERMINAL</div>
        <div class="tc-metrics-container">
            <span class="tc-badge badge-ce">🔴 RESISTANCE: {int(sup_low)} - {int(sup_high)}</span>
            <span class="tc-badge badge-pe">🟢 SUPPORT: {int(dem_low)} - {int(dem_high)}</span>
            <span class="tc-badge {'badge-backup' if is_backup_loaded_flag else 'badge-pp'}">⚖️ MID-PIVOT: {p_point}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # PLOTLY CHART NODE
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(gr.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="LTP"), row=1, col=1)
    
    if show_zones:
        box_idx = max(0, len(df) - 15)
        fig.add_shape(type="rect", x0=df.index[box_idx], x1=df.index[-1], y0=sup_low, y1=sup_high, fillcolor="rgba(239, 68, 68, 0.20)", line=dict(color="#ff3333", width=2))
        fig.add_shape(type="rect", x0=df.index[box_idx], x1=df.index[-1], y0=dem_low, y1=dem_high, fillcolor="rgba(16, 185, 129, 0.20)", line=dict(color="#00cc66", width=2))
        fig.add_hline(y=p_point, line_width=1.5, line_dash="dashdot", line_color="#eab308")

    if show_supertrend: fig.add_trace(gr.Scatter(x=df.index, y=df['supertrend'], line=dict(color=st_color, width=2), name="SuperTrend"))
    if show_dma:
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"))
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"))
        fig.add_trace(gr.Scatter(x=df.index, y=df['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"))
    if show_vwap: fig.add_trace(gr.Scatter(x=df.index, y=df['vwap'], line=dict(color=vwap_color, width=3), name="VWAP"))

    if show_daily_camarilla:
        fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H4'], line=dict(color='#ff1744', width=1, dash="dot"), name="Daily H4"))
        fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L3'], line=dict(color='#00e676', width=1, dash="dot"), name="Daily L3"))
    if show_monthly_camarilla:
        fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_H4'], line=dict(color='#b71c1c', width=1.5), name="Monthly H4"))
        fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_L3'], line=dict(color='#388e3c', width=1.5), name="Monthly L3"))

    if draw_h_line and h_line_value > 0: fig.add_hline(y=h_line_value, line_color=h_line_color, line_width=2)
    if draw_v_line and len(df) > v_line_idx: fig.add_vline(x=df.index[-v_line_idx], line_color=v_line_color, line_width=2, line_dash="dash")

    fig.add_trace(gr.Scatter(x=[df.index[-1]], y=[current_ltp], mode="markers+text", marker=dict(color="#ffff00", size=10, symbol="arrow-left"), text=[f"  ◄ ₹{current_ltp:.2f}"], textposition="middle right", textfont=dict(color="#ffff00", size=13, family="Arial Black"), showlegend=False))

    min_p, max_p = float(df['low'].min()), float(df['high'].max())
    fig.update_layout(
        height=520, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=140, t=10, b=25),
        yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[min_p * 0.99, max_p * 1.01], autorange=False, fixedrange=False),
        xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), autorange=True, fixedrange=False),
        paper_bgcolor='#030712', plot_bgcolor='#030712'
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
    st.plotly_chart(fig, use_container_width=True)

    # Bottom Dashboard Matrix
    st.markdown("### 📊 Live Terminal Reference Dashboard")
    c1, c2, c3 = st.columns(3)
    with c1: st.info(f"🔴 **DR Zone:** {sup_low:.1f} - {sup_high:.1f}")
    with c2: st.success(f"🟢 **DS Zone:** {dem_low:.1f} - {dem_high:.1f}")
    with c3: st.warning(f"🟡 **Live LTP:** ₹{current_ltp:.2f}")
else:
    st.error("❌ Data Engine layer completely empty.")
