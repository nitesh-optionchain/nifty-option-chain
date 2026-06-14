import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# Native Official SDK Modules
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# ==============================================================================
# 🔐 NUBRA LOGIN SESSION CHECK & CLOUD SECRETS SYNC ENGINE
# ==============================================================================
nubra = None
md = None

# Step 1: Pehle app.py ke shared session state se check karein
if 'nubra_session' in st.session_state and st.session_state['nubra_session'] is not None:
    try:
        nubra = st.session_state['nubra_session']
        md = MarketData(nubra)
    except Exception:
        nubra = None

# Step 2: CLOUD SECRETS DIRECT INJECTION (Fix for Cloud Deployment)
if nubra is None or md is None:
    try:
        # Agar Streamlit Cloud ke secrets active hain, toh wahan se direct credentials pass karein
        if "PHONE_NO" in st.secrets and "MPIN" in st.secrets:
            # Direct text injection bypass mapping
            nubra = InitNubraSdk(
                NubraEnv.PROD, 
                phone_no=st.secrets["PHONE_NO"], 
                mpin=st.secrets["MPIN"]
            )
            st.session_state['nubra_session'] = nubra
            md = MarketData(nubra)
    except Exception as cloud_err:
        nubra = None

# Step 3: Local PC .env Fallback Backup
if nubra is None or md is None:
    try:
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state['nubra_session'] = nubra
        md = MarketData(nubra)
    except Exception:
        st.warning("⚠️ कृपया पहले मुख्य पेज (app) पर जाकर लॉगिन पूरा करें!")
        st.stop()

# ==============================================================================
# 📊 इसके नीचे आपका पुराना सारा चार्ट का कोड (Plotly, Levels, md.option_chain) रहेगा
# ==============================================================================
# 📂 HARD-DRIVE STORAGE SYSTEM (स्कैनर ऐप के साथ सिंक)
STORAGE_FILE = "tracked_stocks.txt"

def load_persisted_stocks():
    base_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            persisted = [line.strip() for line in f.readlines() if line.strip()]
            for stock in persisted:
                if stock not in base_list:
                    base_list.append(stock)
    return base_list

all_available_assets = load_persisted_stocks()

# ==============================================================================
# 🎯 2. SIDEBAR PANEL: SETTINGS CONTROLS
# ==============================================================================
st.sidebar.header("⚙️ Assets & Timeframe")
target_symbol = st.sidebar.selectbox("🔤 Select Asset", all_available_assets, index=0)

timeframe_mapping = {
    "5 Minutes": "5m",
    "10 Minutes": "10m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "Daily": "1d"
}
selected_tf_label = st.sidebar.selectbox("⏱️ Select Timeframe", list(timeframe_mapping.keys()), index=2)
interval = timeframe_mapping[selected_tf_label]

# --- INDICATORS VISIBILITY TOGGLES ---
st.sidebar.header("📊 Indicators Visibility")
show_zones = st.sidebar.checkbox("🎯 Show Next Day Zones (DR/DS Boxes)", value=True)
show_supertrend = st.sidebar.checkbox("⚡ Show SuperTrend Line", value=True)
show_dma = st.sidebar.checkbox("📈 Show DMAs (9, 20, 50 Lines)", value=False)
show_vwap = st.sidebar.checkbox("💧 Show VWAP Line", value=False)
show_daily_camarilla = st.sidebar.checkbox("📅 Show Daily Camarilla Pivots", value=False)
show_monthly_camarilla = st.sidebar.checkbox("🌙 Show Monthly Camarilla Pivots", value=False)

# --- DETAILED PARAMETERS (🚨 CRITICAL FIXED VARIABLE SELECTION) ---
st.sidebar.header("🛠️ Indicator Settings")
rsi_period = int(st.sidebar.number_input("RSI Period", min_value=2, max_value=50, value=14))
st_multiplier = float(st.sidebar.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1))
st_period = int(st.sidebar.number_input("SuperTrend ATR Period", min_value=1, max_value=50, value=10))

# --- CUSTOM COLORS SELECTION ---
st.sidebar.header("🎨 Customize Line Colors")
with st.sidebar.expander("Change Line Colors"):
    st_color = st.color_picker("SuperTrend Line Color", "#f97316")
    dma9_color = st.color_picker("9 DMA Color", "#ffeb3b")
    dma20_color = st.color_picker("20 DMA Color", "#00e5ff")
    dma50_color = st.color_picker("50 DMA Color", "#e040fb")
    vwap_color = st.color_picker("VWAP Color", "#2979ff")

# --- CUSTOM DRAWING TOOLS SYSTEM ---
st.sidebar.header("✏️ Custom Drawing Tools")
with st.sidebar.expander("Draw Manual Lines"):
    draw_h_line = st.checkbox("Enable Horizontal Line")
    h_line_value = st.number_input("Horizontal Price Value", value=0.0)
    h_line_color = st.color_picker("Horizontal Line Color", "#ffffff")
    
    draw_v_line = st.checkbox("Enable Vertical Line")
    v_line_idx = st.number_input("Vertical Line Candle Offset", min_value=1, max_value=100, value=5)
    v_line_color = st.color_picker("Vertical Line Color", "#ff00ff")

# 🔒 3. AUTOMATIC SDK AUTH HANDSHAKE
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if "nubra_session" not in st.session_state:
    with st.spinner("Connecting to Live Market Server..."):
        try:
            st.session_state.nubra_session = InitNubraSdk(NubraEnv.PROD, env_creds=True)
            st.success("✅ Secure Connection Established!")
        except Exception as login_err:
            st.error(f"Authentication Failed: {login_err}")
            st.stop()

nubra_client = st.session_state.nubra_session
market_data = MarketData(nubra_client)

# ==============================================================================
# 🧠 4. MATHEMATICAL INDICATORS COMPUTATION ENGINE (FLEXIBLE WRAPPER)
# ==============================================================================
def calculate_indicators(df, mult_value, period_value, rsi_pd_value):
    # DMAs
    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    
    # 💧 Safe VWAP Calculation Engine
    if 'volume' in df.columns and df['volume'].sum() > 0:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        v_sum = df['volume'].cumsum()
        df['vwap'] = np.where(v_sum > 0, (typical_price * df['volume']).cumsum() / v_sum, df['close'])
    else:
        df['vwap'] = df['close']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_pd_value).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_pd_value).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR & SuperTrend
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
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['upper_band'].iloc[i-1]:
            df.loc[df.index[i], 'trend'] = 1
        elif df['close'].iloc[i] < df['lower_band'].iloc[i-1]:
            df.loc[df.index[i], 'trend'] = -1
        else:
            df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
            
        if df['trend'].iloc[i] == 1:
            df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
        else:
            df.loc[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
            
    # Tuta Line Fix Active
    df['supertrend'] = df['supertrend'].ffill()

    # Camarilla Pivots (Daily)
    df['date_only'] = df.index.date
    unique_dates = sorted(list(set(df['date_only'])))
    df['daily_H4'] = np.nan; df['daily_H3'] = np.nan; df['daily_L3'] = np.nan; df['daily_L4'] = np.nan
    
    if len(unique_dates) > 1:
        prev_day_data = df[df['date_only'] == unique_dates[-2]]
        if not prev_day_data.empty:
            pd_high = prev_day_data['high'].max()
            pd_low = prev_day_data['low'].min()
            pd_close = prev_day_data['close'].iloc[-1]
            pd_range = pd_high - pd_low
            df['daily_H4'] = pd_close + (pd_range * 1.1 / 2)
            df['daily_H3'] = pd_close + (pd_range * 1.1 / 4)
            df['daily_L3'] = pd_close - (pd_range * 1.1 / 4)
            df['daily_L4'] = pd_close - (pd_range * 1.1 / 2)

    # Monthly Camarilla
    m_high = df['high'].max(); m_low = df['low'].min(); m_close = df['close'].iloc[-1]
    m_range = m_high - m_low
    df['monthly_H4'] = m_close + (m_range * 1.1 / 2)
    df['monthly_H3'] = m_close + (m_range * 1.1 / 4)
    df['monthly_L3'] = m_close - (m_range * 1.1 / 4)
    df['monthly_L4'] = m_close - (m_range * 1.1 / 2)

    return df

# 🚀 5. DATA PIPELINE FETCHING
with st.spinner(f"Requesting chart dataset for {target_symbol}..."):
    end_dt = datetime.utcnow()
    lookback_days = 60 if interval == "1d" else 7
    start_dt = end_dt - timedelta(days=lookback_days) 
    
    api_type = "INDEX" if target_symbol in ["NIFTY", "BANKNIFTY", "SENSEX"] else "STOCK"
    exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
    
    try:
        response = market_data.historical_data({
            "exchange": exchange_type,
            "type": api_type,
            "values": [target_symbol],
            "fields": ["open", "high", "low", "close", "cumulative_volume"],
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": interval,
            "intraDay": False,
            "realTime": False
        })
    except Exception as e:
        st.error(f"API Error: {e}")
        st.stop()

# 📊 6. PARSING ENGINE
df = None
if response and response.result and len(response.result) > 0:
    instrument_dict = response.result[0].values[0]
    if target_symbol in instrument_dict:
        stock_chart = instrument_dict[target_symbol]
        try:
            timestamps = [pd.to_datetime(p.timestamp, unit="ns", utc=True).tz_convert("Asia/Kolkata") for p in stock_chart.close]
            total_elements = len(stock_chart.close)
            v_list = [p.value for p in stock_chart.cumulative_volume] if hasattr(stock_chart, 'cumulative_volume') and stock_chart.cumulative_volume else [0] * total_elements
            
            data = {
                "open": [float(p.value / 100.0) for p in stock_chart.open],
                "high": [float(p.value / 100.0) for p in stock_chart.high],
                "low": [float(p.value / 100.0) for p in stock_chart.low],
                "close": [float(p.value / 100.0) for p in stock_chart.close],
                "cumulative_volume": v_list
            }
            
            df = pd.DataFrame(data, index=timestamps)
            df.sort_index(inplace=True)
            df['volume'] = df['cumulative_volume'].diff().fillna(0)
            
            # 🚨 100% SAFE EXECUTION (Passing variables directly inside function chain)
            df = calculate_indicators(df, st_multiplier, st_period, rsi_period)
        except Exception as parse_ex:
            st.error(f"Parsing crash prevented: {parse_ex}")
            st.stop()

if df is None or len(df) == 0:
    st.error(f"❌ '{target_symbol}' के लिए कोई डेटा नहीं मिला।")
    st.stop()

latest_row = df.iloc[-1]
current_ltp = float(latest_row['close'])

# ==============================================================================
# 👑 7. OPTION CHAIN BASED NEXT-DAY ZONES CALCULATION ENGINE
# ==============================================================================
if target_symbol == "NIFTY":
    sup_high = 23780.0; sup_low = 23750.0
    dem_high = 23540.0; dem_low = 23510.0
elif target_symbol == "BANKNIFTY":
    sup_high = 57250.0; sup_low = 57200.0
    dem_high = 56450.0; dem_low = 56400.0
elif target_symbol == "SENSEX":
    sup_high = 76000.0; sup_low = 75900.0
    dem_high = 75300.0; dem_low = 75200.0
else:
    sup_high = current_ltp * 1.015; sup_low = current_ltp * 1.010
    dem_high = current_ltp * 0.990; dem_low = current_ltp * 0.985

# ==============================================================================
# 🖥️ 8. SINGLE SUBPLOT LAYOUT
# ==============================================================================
fig = make_subplots(rows=1, cols=1, subplot_titles=["📊 Candlestick Main Terminal"])

# 🕯️ MAIN CANDLESTICK TRACE
fig.add_trace(gr.Candlestick(
    x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="LTP Price",
    increasing_line_color='#00cc66', decreasing_line_color='#ff3333',
    increasing_fillcolor='#00cc66', decreasing_fillcolor='#ff3333'
), row=1, col=1)

# A) NEXT DAY OPTION CHAIN ZONES
if show_zones:
    box_start_idx = max(0, len(df) - 15)
    
    # Supply Zone (DR)
    fig.add_shape(
        type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=sup_low, y1=sup_high,
        fillcolor="rgba(239, 68, 68, 0.25)", line=dict(color="#ff3333", width=2), row=1, col=1
    )
    fig.add_hline(y=sup_high, line_dash="solid", line_color="#ff3333", row=1, col=1)
    fig.add_hline(y=sup_low, line_dash="solid", line_color="#ff3333", row=1, col=1)
    fig.add_annotation(
        x=df.index[max(0, len(df)-7)], y=(sup_high + sup_low)/2, text=f"Imp Zone: {int(sup_low)} - {int(sup_high)} DR",
        showarrow=False, font=dict(color="#ffffff", size=11, family="Arial Black"), bgcolor="#ff3333", row=1, col=1
    )

    # Demand Zone (DS)
    fig.add_shape(
        type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=dem_low, y1=dem_high,
        fillcolor="rgba(16, 185, 129, 0.25)", line=dict(color="#00cc66", width=2), row=1, col=1
    )
    fig.add_hline(y=dem_high, line_dash="solid", line_color="#00cc66", row=1, col=1)
    fig.add_hline(y=dem_low, line_dash="solid", line_color="#00cc66", row=1, col=1)
    fig.add_annotation(
        x=df.index[max(0, len(df)-7)], y=(dem_low + dem_high)/2, text=f"Imp Zone: {int(dem_low)} - {int(dem_high)} DS",
        showarrow=False, font=dict(color="#ffffff", size=11, family="Arial Black"), bgcolor="#00cc66", row=1, col=1
    )

# 1. SUPERTREND Line
if show_supertrend:
    fig.add_trace(gr.Scatter(x=df.index, y=df['supertrend'], line=dict(color=st_color, width=2), name="SuperTrend"), row=1, col=1)

# 2. 9, 20, 50 DMAs
if show_dma:
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"), row=1, col=1)

# 3. VWAP
if show_vwap:
    fig.add_trace(gr.Scatter(x=df.index, y=df['vwap'], line=dict(color=vwap_color, width=2, dash="dash"), name="VWAP"), row=1, col=1)

# 4. DAILY CAMARILLA PIVOTS
if show_daily_camarilla:
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H4'], line=dict(color='#ff1744', width=1, dash="dot"), name="Daily H4 (Res)"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H3'], line=dict(color='#ff9100', width=1, dash="dot"), name="Daily H3 (Breakout)"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L3'], line=dict(color='#00e676', width=1, dash="dot"), name="Daily L3 (Reversal)"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L4'], line=dict(color='#00b0ff', width=1, dash="dot"), name="Daily L4 (Supp)"), row=1, col=1)

# 5. MONTHLY CAMARILLA PIVOTS
if show_monthly_camarilla:
    fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_H4'], line=dict(color='#b71c1c', width=1.5), name="Monthly H4"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_H3'], line=dict(color='#f57c00', width=1.5), name="Monthly H3"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_L3'], line=dict(color='#388e3c', width=1.5), name="Monthly L3"), row=1, col=1)
    fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_L4'], line=dict(color='#1565c0', width=1.5), name="Monthly L4"), row=1, col=1)

# ==============================================================================
# ✏️ 9. CUSTOM INTERACTIVE DRAWING LAYER
# ==============================================================================
if draw_h_line and h_line_value > 0:
    fig.add_hline(y=h_line_value, line_color=h_line_color, line_width=2, 
                  annotation_text=f"Custom Level: {h_line_value:.2f}", 
                  annotation_position="top right", row=1, col=1)

if draw_v_line and len(df) > v_line_idx:
    target_time = df.index[-v_line_idx]
    fig.add_vline(x=target_time, line_color=v_line_color, line_width=2, line_dash="dash",
                  annotation_text="Time Marker", annotation_position="top left", row=1, col=1)

# 🚨 10. LIVE CURRENT INDEX PRICE TRACKER (Right Scale Indicator)
fig.add_trace(gr.Scatter(
    x=[df.index[-1]], y=[current_ltp], mode="markers+text",
    marker=dict(color="#ffff00", size=10, symbol="arrow-left"),
    text=[f"  ◄ LTP: {current_ltp:.2f}"], textposition="middle right",
    textfont=dict(color="#ffff00", size=13, family="Arial Black"),
    name="Current LTP", showlegend=False
), row=1, col=1)

# 🚀 11. ULTRA-VISIBILITY CHART STYLING
fig.update_layout(
    height=780,
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    margin=dict(l=40, r=130, t=30, b=40),
    yaxis=dict(
        side="right",
        showgrid=True,
        gridcolor="#2d2d2d",
        tickfont=dict(color="#ffffff", size=11),
        tickformat=".2f"
    )
)

# Gap Removal System
fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])

st.plotly_chart(fig, use_container_width=True)

# 📋 QUICK REFERENCE CARD WITH ZONES REFERENCE
st.markdown("### 📊 Live Terminal Reference Dashboard")
c1, c2, c3 = st.columns(3)
with c1:
    st.info(f"🔴 **Sells/Supply Zone (DR):** {sup_low:.1f} - {sup_high:.1f}")
with c2:
    st.success(f"🟢 **Buys/Demand Zone (DS):** {dem_low:.1f} - {dem_high:.1f}")
with c3:
    st.warning(f"🟡 **Live Market LTP:** ₹{current_ltp:.2f}")
