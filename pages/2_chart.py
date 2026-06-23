# pages/2_chart.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh

# 🔒 Persistent Session Authentication
if 'chart_auth_verified' not in st.session_state:
    st.session_state['chart_auth_verified'] = False
if 'chart_page_session' not in st.session_state:
    st.session_state['chart_page_session'] = None

st.markdown("### 📊 TradeClue Live Production Terminal")

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# Server Core Connection Matrix
if not st.session_state['chart_auth_verified']:
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state['chart_page_session'] = client
        st.session_state['chart_auth_verified'] = True
        st.rerun()
    except Exception as e:
        st.error(f"🔴 Live Server Authentication Failed: {e}. Please check credentials.")
        st.stop()

try:
    market_data = MarketData(st.session_state['chart_page_session'])
except Exception as e:
    st.error(f"🔴 SDK Market Data Initialization Failed: {e}")
    st.stop()

# ⏱️ System Refresh Interval (25 Seconds)
st_autorefresh(interval=25000, key="smartwealth_live_terminal_absolute_v100")

# Premium Viewport UI Injections
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
target_symbol = st.sidebar.selectbox("🔤 Select Index Asset", all_available_assets, index=0)

timeframe_mapping = {"5 Minutes": "5m", "10 Minutes": "10m", "15 Minutes": "15m", "30 Minutes": "30m", "Daily": "1d"}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Timeframe", list(timeframe_mapping.keys()), index=2)
interval = timeframe_mapping[selected_tf_label]

show_zones = st.sidebar.checkbox("🎯 Show TradeClue DR/DS & Zones", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=True)
st_multiplier = st.sidebar.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1)
st_period = st.sidebar.number_input("SuperTrend ATR Period", min_value=1, max_value=50, value=10)

# ==============================================================================
# 🚀 DIRECT ABSOLUTE LIVE FETCH PIPELINE (NO SIMULATION FALLBACK ALLOWED)
# ==============================================================================
df = None
try:
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=6)
    api_type = "INDEX" if target_symbol in ["NIFTY", "BANKNIFTY", "SENSEX"] else "STOCK"
    exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
    
    response = market_data.historical_data({
        "exchange": exchange_type, "type": api_type, "values": [target_symbol],
        "fields": ["open", "high", "low", "close"],
        "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "interval": interval, "intraDay": False, "realTime": False
    })
    
    if response and response.result and len(response.result) > 0:
        instrument_dict = response.result[0].values[0]
        if target_symbol in instrument_dict:
            stock_chart = instrument_dict[target_symbol]
            raw_closes = [float(p.value) for p in stock_chart.close]
            
            # Smart Decimal Matrix Adjuster to resolve 100x Scaling issue
            avg_raw = sum(raw_closes) / len(raw_closes)
            scale_factor = 100.0 if avg_raw > 150000 else 1.0
            
            timestamps = [pd.to_datetime(p.timestamp, unit="ns", utc=True).tz_convert("Asia/Kolkata") for p in stock_chart.close]
            df = pd.DataFrame({
                "open": [float(p.value / scale_factor) for p in stock_chart.open],
                "high": [float(p.value / scale_factor) for p in stock_chart.high],
                "low": [float(p.value / scale_factor) for p in stock_chart.low],
                "close": [float(p.value / scale_factor) for p in stock_chart.close]
            }, index=timestamps).sort_index()
except Exception as e:
    st.error(f"🔴 Live Data Fetch Error: {e}")
    st.stop()

if df is None or len(df) == 0:
    st.error("🔴 Server returned empty dataset. Please check if the market is open or token is active.")
    st.stop()

# Indicators Logic
df['vwap'] = df['close']
df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
df['atr'] = df['tr'].rolling(window=int(st_period), min_periods=1).mean()
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

current_ltp = float(df['close'].iloc[-1])

# Dynamic Level Scaling Modules
if target_symbol == "NIFTY":
    dr_level = float(((current_ltp + 15) // 50) * 50 + 50)
    ds_level = float(((current_ltp - 15) // 50) * 50 - 50)
    res_zone_low = dr_level + 15; res_zone_high = dr_level + 35
    sup_zone_low = ds_level - 35; sup_zone_high = ds_level - 15
elif target_symbol == "BANKNIFTY":
    dr_level = float(((current_ltp + 40) // 100) * 100 + 100)
    ds_level = float(((current_ltp - 40) // 100) * 100 - 100)
    res_zone_low = dr_level + 40; res_zone_high = dr_level + 120
    sup_zone_low = ds_level - 120; sup_zone_high = ds_level - 40
else:
    dr_level = current_ltp * 1.004; ds_level = current_ltp * 0.996
    res_zone_low = dr_level * 1.002; res_zone_high = dr_level * 1.004
    sup_zone_low = ds_level * 0.996; sup_zone_high = ds_level * 0.998

p_point = round((dr_level + ds_level + current_ltp) / 3, 2)

st.markdown(f"""
<div class="tc-dashboard-header">
    <div class="tc-title">⚡ {target_symbol} REAL-TIME ACTIVE TERMINAL</div>
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

fig.add_trace(gr.Candlestick(
    x=df_plot['time_str'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], 
    name="LTP", increasing_fillcolor='#22c55e', decreasing_fillcolor='#ef4444',
    increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
), row=1, col=1)

layout_annotations = []
view_candles = df_plot.tail(25) # Exact 25 Candles Constraint

if show_zones:
    box_start_idx = max(0, len(df_plot) - 12)
    x0_val = df_plot['time_str'].iloc[box_start_idx]
    x1_val = df_plot['time_str'].iloc[-1]
    
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=res_zone_low, y1=res_zone_high, fillcolor="rgba(239, 68, 68, 0.22)", line=dict(color="#ef4444", width=1.5))
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=sup_zone_low, y1=sup_zone_high, fillcolor="rgba(34, 197, 94, 0.22)", line=dict(color="#22c55e", width=1.5))
    fig.add_hline(y=dr_level, line_width=1.5, line_dash="dash", line_color="#f87171")
    fig.add_hline(y=ds_level, line_width=1.5, line_dash="dash", line_color="#4ade80")
    fig.add_hline(y=p_point, line_width=1, line_dash="dashdot", line_color="#eab308")

    layout_annotations.append(dict(x=x0_val, y=dr_level, text="🔴 DR LEVEL", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color="#f87171", size=10, family="Arial Black")))
    layout_annotations.append(dict(x=x0_val, y=ds_level, text="🟢 DS LEVEL", showarrow=False, xanchor="left", yanchor="top", font=dict(color="#4ade80", size=10, family="Arial Black")))

if show_supertrend: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['supertrend'], line=dict(color="#f97316", width=2.5), name="SuperTrend"))
if show_vwap: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['vwap'], line=dict(color="#00f0ff", width=2), name="VWAP"))

# Flat non-overlapping LTP Marker Pointer Tag
fig.add_trace(gr.Scatter(
    x=[df_plot['time_str'].iloc[-1]], y=[current_ltp], mode="markers+text", 
    marker=dict(color="#ffff00", size=10, symbol="arrow-left"), 
    text=[f" ◄ ₹{current_ltp:.2f}"], textposition="middle right", 
    textfont=dict(color="#ffff00", size=13, family="Arial Black"),
    cliponaxis=False, showlegend=False
))

low_extreme = float(view_candles['low'].min())
high_extreme = float(view_candles['high'].max())
if show_zones:
    low_extreme = min(low_extreme, sup_zone_low)
    high_extreme = max(high_extreme, res_zone_high)
# Tighter vertical compression factor (0.02) to stretch candle length vertically 
vertical_stretch_factor = (high_extreme - low_extreme) * 0.02

fig.update_layout(
    height=680, autosize=True, margin=dict(l=10, r=160, t=10, b=25), 
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[low_extreme - vertical_stretch_factor, high_extreme + vertical_stretch_factor], autorange=False, fixedrange=False),
    # bargap=0.40 sets standard thin body structures for candles
    xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), type='category', categoryorder='category ascending', range=[df_plot['time_str'].iloc[-25], df_plot['time_str'].iloc[-1]], autorange=False, fixedrange=False),
    bargap=0.40, paper_bgcolor='#030712', plot_bgcolor='#030712',
    annotations=layout_annotations
)

st.plotly_chart(fig, use_container_width=True)
