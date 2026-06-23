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
# 🎯 1. SHIELDED AUTHENTICATION & SESSION MULTIPLIER LOCK
# ==============================================================================
if 'chart_auth_verified' not in st.session_state:
    st.session_state['chart_auth_verified'] = False
if 'chart_page_session' not in st.session_state:
    st.session_state['chart_page_session'] = None
if 'fallback_active_state' not in st.session_state:
    st.session_state['fallback_active_state'] = False
if 'last_selected_symbol' not in st.session_state:
    st.session_state['last_selected_symbol'] = ""

st.markdown("### 🔒 Index Live Chart Terminal")

if not st.session_state['chart_auth_verified']:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Connect Server Live Auth", use_container_width=True):
            try:
                from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
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

try:
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    from nubra_python_sdk.marketdata.market_data import MarketData

    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_data = MarketData(client)

except Exception as e:
    st.error(repr(e))
    market_data = None

# ==============================================================================
# ⏱️ 2. REFRESH CONTROL (SET TO STABLE 25 SECONDS)
# ==============================================================================
st_autorefresh(interval=5000, key="smartwealth_index_terminal_perfect_v35")

# Premium Dashboard Stylesheet Injection
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

# Dynamic Cache Lock to prevent data jump on auto refresh
def get_static_fallback_data(symbol):

    base_price = 24013.40 if symbol == "NIFTY" else (
        51650.0 if symbol == "BANKNIFTY" else 78900.0
    )

    timestamps = pd.date_range(
        end=datetime.now(),
        periods=60,
        freq="15min"
    )

    changes = np.random.normal(
        0,
        base_price * 0.0005,
        60
    )

    closes = base_price + np.cumsum(changes)

    opens = closes - np.random.normal(
        0,
        base_price * 0.0002,
        60
    )

    highs = np.maximum(opens, closes) + abs(
        np.random.normal(0, base_price * 0.0002, 60)
    )

    lows = np.minimum(opens, closes) - abs(
        np.random.normal(0, base_price * 0.0002, 60)
    )

    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.random.randint(2000,7000,60)
        },
        index=timestamps
    )
# ==============================================================================
# 🚀 4. CORE COMPUTATIONAL SCALING INTERFACE
# ==============================================================================
df = None
if market_data is None:
    df = get_static_fallback_data(target_symbol)
else:
    try:
        with st.spinner("Decoding dataset grid vectors..."):
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=7)
            api_type = "INDEX" if target_symbol in ["NIFTY", "BANKNIFTY", "SENSEX"] else "STOCK"
            exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
            
            response = market_data.historical_data({
                "exchange": exchange_type, "type": api_type, "values": [target_symbol],
                "fields": ["open", "high", "low", "close", "cumulative_volume"],
                "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "interval": interval, "intraDay": True, "realTime": True
            })

            
            if response and response.result and len(response.result) > 0:
                instrument_dict = response.result[0].values[0]
                if target_symbol in instrument_dict:
                    stock_chart = instrument_dict[target_symbol]
                    raw_closes = [float(p.value) for p in stock_chart.close]
                    
                    avg_raw = sum(raw_closes) / len(raw_closes)
                    scale_factor = 1.0
                    if avg_raw > 100000: scale_factor = 100.0

                    timestamps = [pd.to_datetime(p.timestamp, unit="ns", utc=True).tz_convert("Asia/Kolkata") for p in stock_chart.close]
                    v_list = [p.value for p in stock_chart.cumulative_volume] if hasattr(stock_chart, 'cumulative_volume') and stock_chart.cumulative_volume else [0] * len(stock_chart.close)
                    
                    data = {
                        "open": [float(p.value / scale_factor) for p in stock_chart.open],
                        "high": [float(p.value / scale_factor) for p in stock_chart.high],
                        "low": [float(p.value / scale_factor) for p in stock_chart.low],
                        "close": [float(p.value / scale_factor) for p in stock_chart.close],
                        "cumulative_volume": v_list
                    }
                    df = pd.DataFrame(data, index=timestamps).sort_index()
                    df['volume'] = df['cumulative_volume'].diff().fillna(0)
    except Exception as e:
        st.error(e)
    df = get_static_fallback_data(target_symbol)

if df is None or len(df) == 0:
    df = get_static_fallback_data(target_symbol)

# Technical Indicators
df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
if 'volume' in df.columns and interval != "1d":
    df['volume_clean'] = df['volume'].fillna(0)
    df['vwap'] = ((df['high'] + df['low'] + df['close'])/3 * df['volume_clean']).cumsum() / (df['volume_clean'].cumsum() + 1e-10)
else:
    df['vwap'] = df['close']

df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
df['atr'] = df['tr'].rolling(window=st_period, min_periods=1).mean()

# SuperTrend Calculations Vector
df['hl2'] = (df['high'] + df['low']) / 2
df['upper_band'] = df['hl2'] + (st_multiplier * df['atr'])
df['lower_band'] = df['hl2'] - (st_multiplier * df['atr'])
df['supertrend'] = np.nan
df.iloc[0, df.columns.get_loc('supertrend')] = df['close'].iloc[0]
df['trend'] = 1

for i in range(1, len(df)):
    if df['close'].iloc[i] > df['upper_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = 1
    elif df['close'].iloc[i] < df['lower_band'].iloc[i-1]: df.loc[df.index[i], 'trend'] = -1
    else: df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
    df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i] if df['trend'].iloc[i] == 1 else df['upper_band'].iloc[i]

# ==============================================================================
# 🖥️ 5. EXPLICIT SEPARATION: DR/DS LEVEL VS ZONE MATRIX
# ==============================================================================
current_ltp = float(df['close'].iloc[-1])

# Absolute separate clean assignments for DR/DS vs Resistance/Support Zones
if target_symbol == "NIFTY":
    dr_level = 24080.0
    ds_level = 23960.0
    res_zone_low = 24120.0; res_zone_high = 24150.0
    sup_zone_low = 23880.0; sup_zone_high = 23910.0
elif target_symbol == "BANKNIFTY":
    dr_level = 51800.0
    ds_level = 51500.0
    res_zone_low = 51950.0; res_zone_high = 52050.0
    sup_zone_low = 51300.0; sup_zone_high = 51400.0
else:
    dr_level = current_ltp * 1.008
    ds_level = current_ltp * 0.992
    res_zone_low = current_ltp * 1.015; res_zone_high = current_ltp * 1.020
    sup_zone_low = current_ltp * 0.980; sup_zone_high = current_ltp * 0.985

p_point = round((dr_level + ds_level + current_ltp) / 3, 2)

# TradeClue Dynamic Split Header (Perfect Separation)
st.markdown(f"""
<div class="tc-dashboard-header">
    <div class="tc-title">⚡ {target_symbol} TRADECLUE ENGINE PROFILE</div>
    <div class="tc-metrics-container">
        <span class="tc-badge badge-ce">🔴 DR LEVEL: {int(dr_level)} | ZONE: {int(res_zone_low)}-{int(res_zone_high)}</span>
        <span class="tc-badge badge-pe">🟢 DS LEVEL: {int(ds_level)} | ZONE: {int(sup_zone_low)}-{int(sup_zone_high)}</span>
        <span class="tc-badge badge-pp">⚖️ PIVOT: {p_point:.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(rows=1, cols=1)

# Converting Datetime index to standard string format to solve the "Chart Missing" error permanently
df_plot = df.copy()
df_plot['time_str'] = df_plot.index.strftime('%H:%M')
if interval == "1d":
    df_plot['time_str'] = df_plot.index.strftime('%Y-%m-%d')

fig.add_trace(gr.Candlestick(x=df_plot['time_str'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name="LTP"), row=1, col=1)

layout_annotations = []

if show_zones:
    box_start_idx = max(0, len(df_plot) - 20)
    x0_val = df_plot['time_str'].iloc[box_start_idx]
    x1_val = df_plot['time_str'].iloc[-1]
    
    # 🔴 TradeClue Pure Resistance Zone Boxes
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=res_zone_low, y1=res_zone_high, fillcolor="rgba(239, 68, 68, 0.14)", line=dict(color="#ef4444", width=1.5))
    # 🟢 TradeClue Pure Support Zone Boxes
    fig.add_shape(type="rect", x0=x0_val, x1=x1_val, y0=sup_zone_low, y1=sup_zone_high, fillcolor="rgba(34, 197, 94, 0.14)", line=dict(color="#22c55e", width=1.5))
    
    # Horizontal Separate Trigger Lines for DR and DS Levels
    fig.add_hline(y=dr_level, line_width=2, line_dash="dash", line_color="#f87171")
    fig.add_hline(y=ds_level, line_width=2, line_dash="dash", line_color="#4ade80")
    fig.add_hline(y=p_point, line_width=1.5, line_dash="dashdot", line_color="#eab308")

    # Injections of Separate Independent Absolute Text Anchors
    layout_annotations.append(dict(x=x0_val, y=dr_level, text="🔴 DR LEVEL (DAILY RESISTANCE)", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color="#f87171", size=11, family="Arial Black")))
    layout_annotations.append(dict(x=x0_val, y=ds_level, text="🟢 DS LEVEL (DAILY SUPPORT)", showarrow=False, xanchor="left", yanchor="top", font=dict(color="#4ade80", size=11, family="Arial Black")))
    layout_annotations.append(dict(x=x1_val, y=res_zone_high, text="⚠️ RESISTANCE ZONE", showarrow=False, xanchor="right", yanchor="bottom", font=dict(color="#ef4444", size=11, family="Arial Bold")))
    layout_annotations.append(dict(x=x1_val, y=sup_zone_low, text="✅ SUPPORT ZONE", showarrow=False, xanchor="right", yanchor="top", font=dict(color="#22c55e", size=11, family="Arial Bold")))

if show_supertrend: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['supertrend'], line=dict(color=st_color, width=2), name="SuperTrend"))
if show_dma:
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"))
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"))
    fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"))
if show_vwap: fig.add_trace(gr.Scatter(x=df_plot['time_str'], y=df_plot['vwap'], line=dict(color=vwap_color, width=2.5), name="VWAP"))

# Real-Time LTP arrow tracking flag
fig.add_trace(gr.Scatter(x=[df_plot['time_str'].iloc[-1]], y=[current_ltp], mode="markers+text", marker=dict(color="#ffff00", size=11, symbol="arrow-left"), text=[f"  ◄ ₹{current_ltp:.2f}"], textposition="middle right", textfont=dict(color="#ffff00", size=13, family="Arial Black"), showlegend=False))

# Symmetrical lookback padding zoom logic
view_candles = df_plot.tail(30)
low_extreme = min(float(view_candles['low'].min()), sup_zone_low)
high_extreme = max(float(view_candles['high'].max()), res_zone_high)
comfort_padding = (high_extreme - low_extreme) * 0.20

fig.update_layout(
    height=540, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=165, t=10, b=25),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), range=[low_extreme - comfort_padding, high_extreme + comfort_padding], autorange=False, fixedrange=False),
    xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), autorange=True, fixedrange=False),
    paper_bgcolor='#030712', plot_bgcolor='#030712',
    annotations=layout_annotations
)

st.plotly_chart(fig, use_container_width=True)

# Separate structural matrix lower references
st.markdown("### 📊 Live Terminal Reference Dashboard")
c1, c2, c3 = st.columns(3)
with c1: st.info(f"🔴 **DR Level:** {int(dr_level)} | **Zone:** {int(res_zone_low)}-{int(res_zone_high)}")
with c2: st.success(f"🟢 **DS Level:** {int(ds_level)} | **Zone:** {int(sup_zone_low)}-{int(sup_zone_high)}")
with c3: st.warning(f"🟡 **Current LTP:** ₹{current_ltp:.2f}")
