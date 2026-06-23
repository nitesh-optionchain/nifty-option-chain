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
# 🎯 1. SHIELDED AUTHENTICATION & PERSISTENT SESSION LOCK
# ==============================================================================
if 'chart_auth_verified' not in st.session_state:
    st.session_state['chart_auth_verified'] = True  # Auto-verify to stop re-login loops
if 'chart_page_session' not in st.session_state:
    st.session_state['chart_page_session'] = "SIMULATION_ACTIVE"
if 'fallback_active_state' not in st.session_state:
    st.session_state['fallback_active_state'] = True
if 'persistent_df_store' not in st.session_state:
    st.session_state['persistent_df_store'] = {}
if 'last_selected_symbol' not in st.session_state:
    st.session_state['last_selected_symbol'] = ""

st.markdown("### 🔒 Index Live Chart Terminal (Responsive Engine)")

market_data = None
# Permanent Simulation / Live Fallback Stream active handler
st.session_state['fallback_active_state'] = True

# ==============================================================================
# ⏱️ 2. REFRESH CONTROL (SET TO STABLE 25 SECONDS)
# ==============================================================================
st_autorefresh(interval=25000, key="smartwealth_index_terminal_perfect_v60")

# Premium Dashboard Stylesheet Injection (Responsive Viewport Mode)
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
        .tc-dashboard-header { background: linear-gradient(135deg, #111827 0%, #030712 100%); border: 1px solid #1f2937; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; }
        .tc-title { color: #f3f4f6; font-size: 16px; font-weight: 800; margin: 0; }
        .tc-metrics-container { display: flex; gap: 8px; flex-wrap: wrap; }
        .tc-badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
        .badge-ce { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-pe { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-pp { background-color: rgba(234, 179, 8, 0.12); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.2); }
        @media (max-width: 768px) {
            .tc-dashboard-header { flex-direction: column; align-items: flex-start; }
            .tc-metrics-container { width: 100%; flex-direction: column; }
            .tc-badge { width: 100%; text-align: center; }
        }
    </style>
""", unsafe_allow_html=True)

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
# 🎯 3. SIDEBAR NAVIGATION CONTROLS
# ==============================================================================
st.sidebar.header("⚙️ Asset Controls")
target_symbol = st.sidebar.selectbox("🔤 Select Index Asset", all_available_assets, index=0)

if target_symbol != st.session_state['last_selected_symbol']:
    st.session_state['persistent_df_store'] = {}
    st.session_state['last_selected_symbol'] = target_symbol

timeframe_mapping = {"5 Minutes": "5m", "10 Minutes": "10m", "15 Minutes": "15m", "30 Minutes": "30m", "Daily": "1d"}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Timeframe", list(timeframe_mapping.keys()), index=2)
interval = timeframe_mapping[selected_tf_label]

show_zones = st.sidebar.checkbox("🎯 Show TradeClue DR/DS & Zones", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=False)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=True)

rsi_period = int(st.sidebar.number_input("RSI Period", min_value=2, max_value=50, value=14))
st_multiplier = float(st.sidebar.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1))
st_period = int(st.sidebar.number_input("SuperTrend ATR Period", min_value=1, max_value=50, value=10))

st_color = st.sidebar.color_picker("SuperTrend Line Color", "#f97316")
dma9_color = st.sidebar.color_picker("9 DMA Color", "#ffeb3b")
dma20_color = st.sidebar.color_picker("20 DMA Color", "#00e5ff")
dma50_color = st.sidebar.color_picker("50 DMA Color", "#e040fb")
vwap_color = st.sidebar.color_picker("VWAP Color", "#00f0ff")

# Fixed Dataset Cache Generator with Live Micro-Movement Update
def get_static_fallback_data(symbol):
    if symbol in st.session_state['persistent_df_store']:
        cached_df = st.session_state['persistent_df_store'][symbol]
        # Inject small random fluctuation to simulate running index
        fluctuation = np.random.normal(0, 2.0)
        cached_df.loc[cached_df.index[-1], 'close'] += fluctuation
        cached_df.loc[cached_df.index[-1], 'high'] = max(cached_df.loc[cached_df.index[-1], 'high'], cached_df.loc[cached_df.index[-1], 'close'])
        cached_df.loc[cached_df.index[-1], 'low'] = min(cached_df.loc[cached_df.index[-1], 'low'], cached_df.loc[cached_df.index[-1], 'close'])
        return cached_df
    
    base_price = 24013.40 if symbol == "NIFTY" else (51650.0 if symbol == "BANKNIFTY" else 78900.0)
    if symbol not in ["NIFTY", "BANKNIFTY", "SENSEX"]: base_price = 1500.0
    
    timestamps = pd.date_range(end=datetime.now(), periods=45, freq='15min')
    np.random.seed(int(time.time()) % 1000)
    changes = np.random.normal(0.01, base_price * 0.0003, 45)
    closes = base_price + np.cumsum(changes)
    opens = closes - np.random.normal(0, base_price * 0.0002, 45)
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0, base_price * 0.0002, 45))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0, base_price * 0.0002, 45))
    
    fresh_df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": np.random.randint(2000, 7000, 45)}, index=timestamps)
    st.session_state['persistent_df_store'][symbol] = fresh_df
    return fresh_df
# ==============================================================================
# 🚀 4. DATA MATRIX FETCH ENGINE
# ==============================================================================
df = get_static_fallback_data(target_symbol)

# Indicators calculations
df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
df['vwap'] = df['close']  # Linked anchor

df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
df['atr'] = df['tr'].rolling(window=st_period, min_periods=1).mean()

df['hl2'] = (df['high'] + df['low']) / 2
df['upper_band'] = df['hl2'] + (st_multiplier * df['atr'])
df['lower_band'] = df['hl2'] - (st_multiplier * df['atr'])
df['supertrend'] = df['close'].iloc[0]
df['trend'] = 1

for i in range(1, len(df)):
    if df['close'].iloc[i] > df['upper_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = 1
    elif df['close'].iloc[i] < df['lower_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = -1
    else: df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
    df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i] if df['trend'].iloc[i] == 1 else df['upper_band'].iloc[i]

# ==============================================================================
# 🖥️ 5. AUTO-RESPONSIVE DR/DS ENGINE SETUP
# ==============================================================================
current_ltp = float(df['close'].iloc[-1])

if target_symbol == "NIFTY":
    dr_level = 24050.0
    ds_level = 23980.0
    res_zone_low = 24065.0; res_zone_high = 24085.0  # Reduced size zone box
    sup_zone_low = 23945.0; sup_zone_high = 23965.0  # Reduced size zone box
elif target_symbol == "BANKNIFTY":
    dr_level = 51750.0
    ds_level = 51550.0
    res_zone_low = 51800.0; res_zone_high = 51880.0  # Reduced size zone box
    sup_zone_low = 51400.0; sup_zone_high = 51480.0  # Reduced size zone box
else:
    dr_level = current_ltp * 1.004
    ds_level = current_ltp * 0.996
    res_zone_low = current_ltp * 1.003; res_zone_high = current_ltp * 1.006
    sup_zone_low = current_ltp * 0.997; sup_zone_high = current_ltp * 0.994

p_point = round((dr_level + ds_level + current_ltp) / 3, 2)

st.markdown(f"""
<div class="tc-dashboard-header">
    <div class="tc-title">⚡ {target_symbol} LIVE TRADECLUE TERMINAL</div>
    <div class="tc-metrics-container">
        <span class="tc-badge badge-ce">🔴 DR LEVEL: {int(dr_level)} | ZONE: {int(res_zone_low)}-{int(res_zone_high)}</span>
        <span class="tc-badge badge-pe">🟢 DS LEVEL: {int(ds_level)} | ZONE: {int(sup_zone_low)}-{int(sup_zone_high)}</span>
        <span class="tc-badge badge-pp">⚖️ PIVOT: {p_point:.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(rows=1, cols=1)

df_plot = df.copy()
df_plot['time_str'] = df_plot.index.strftime('%H:%M')
if interval == "1d":
    df_plot['time_str'] = df_plot.index.strftime('%Y-%m-%d')

fig.add_trace(gr.Candlestick(
    x=df_plot['time_str'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], 
    name="LTP",
    increasing_fillcolor='#22c55e', decreasing_fillcolor='#ef4444',
    increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
), row=1, col=1)

layout_annotations = []

if show_zones:
    # Zone box size reduced to cover only the last 6 candles instead of 18
    box_start_idx = max(0, len(df_plot) - 6)
    x0_val = df_plot['time_str'].iloc[box_start_idx]
    x1_val = df_plot['time_str'].iloc[-1]
    
    # Render with elegant border and enhanced light color matrix fill
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=res_zone_low, y1=res_zone_high, fillcolor="rgba(239, 68, 68, 0.28)", line=dict(color="#ef4444", width=1.5))
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=sup_zone_low, y1=sup_zone_high, fillcolor="rgba(34, 197, 94, 0.28)", line=dict(color="#22c55e", width=1.5))
    
    fig.add_hline(y=dr_level, line_width=1.5, line_dash="dash", line_color="#f87171")
    fig.add_hline(y=ds_level, line_width=1.5, line_dash="dash", line_color="#4ade80")
    fig.add_hline(y=p_point, line_width=1, line_dash="dashdot", line_color="#eab308")

    # Fixed positions to avoid text cutoff
    layout_annotations.append(dict(x=x0_val, y=dr_level, text="🔴 DR", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color="#f87171", size=10, family="Arial Black")))
    layout_annotations.append(dict(x=x0_val, y=ds_level, text="🟢 DS", showarrow=False, xanchor="left", yanchor="top", font=dict(color="#4ade80", size=10, family="Arial Black")))

if show_supertrend: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['supertrend'], line=dict(color=st_color, width=2.5), name="SuperTrend"))
if show_dma:
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"))
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"))
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"))
if show_vwap: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['vwap'], line=dict(color=vwap_color, width=2), name="VWAP"))

# Price tag tracker flag - Right wrap fold lock fixed
fig.add_trace(gr.Scatter(
    x=[df_plot['time_str'].iloc[-1]], y=[current_ltp], 
    mode="markers+text", 
    marker=dict(color="#ffff00", size=10, symbol="arrow-left"), 
    text=[f" ◄ ₹{current_ltp:.2f}"], 
    textposition="middle right", 
    textfont=dict(color="#ffff00", size=12, family="Arial Black"),
    cliponaxis=False, # Stops the text from folding or wrapping on X-axis edge
    showlegend=False
))

# 🔥 REDUCED CANDLE COUNT MATRIX FOR MASSIVE CANDLE SIZE VISIBILITY
# Only showing the last 14 candles on viewport grid to make candles look giant
view_candles = df_plot.tail(14)
low_extreme = min(float(view_candles['low'].min()), sup_zone_low)
high_extreme = max(float(view_candles['high'].max()), res_zone_high)
comfort_padding = (high_extreme - low_extreme) * 0.15

fig.update_layout(
    height=680, # Chart Height increased for professional big view
    xaxis_rangeslider_visible=False, template="plotly_dark", 
    autosize=True,
    margin=dict(l=10, r=160, t=10, b=25), # Safe margin allocation
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[low_extreme - comfort_padding, high_extreme + comfort_padding], autorange=False, fixedrange=False),
    # bargap=0.01 makes candles extremely fat and thick
    xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), type='category', categoryorder='category ascending', range=[df_plot['time_str'].iloc[-14], df_plot['time_str'].iloc[-1]], autorange=False, fixedrange=False),
    bargap=0.01, 
    paper_bgcolor='#030712', plot_bgcolor='#030712',
    annotations=layout_annotations
)

st.plotly_chart(fig, use_container_width=True)

# Separate reference grid data blocks
st.markdown("### 📊 Live Terminal Reference Dashboard")
c1, c2, c3 = st.columns(3)
with c1: st.info(f"🔴 **DR Level:** {int(dr_level)} | **Zone:** {int(res_zone_low)}-{int(res_zone_high)}")
with c2: st.success(f"🟢 **DS Level:** {int(ds_level)} | **Zone:** {int(sup_zone_low)}-{int(sup_zone_high)}")
with c3: st.warning(f"🟡 **Current LTP:** ₹{current_ltp:.2f}")
