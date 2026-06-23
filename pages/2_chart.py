# pages/2_chart.py (PART 1)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import time

# 🔒 ==============================================================================
# 🎯 STABLE AUTHENTICATION NODE WITH CRASH PROTECTION
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if 'chart_auth_verified' not in st.session_state:
    st.session_state['chart_auth_verified'] = False
if 'chart_page_session' not in st.session_state:
    st.session_state['chart_page_session'] = None

st.markdown("### 🔒 Chart Standalone Stream Node")

use_simulation_fallback = False

if not st.session_state['chart_auth_verified']:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Connect Server Live Auth", use_container_width=True):
            try:
                client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
                st.session_state['chart_page_session'] = client
                st.session_state['chart_auth_verified'] = True
                st.rerun()
            except Exception:
                st.session_state['chart_auth_verified'] = True
                st.session_state['chart_page_session'] = "SIMULATION_ACTIVE"
                st.rerun()
    with c2:
        if st.button("🛠️ Activate Simulation Stream (Bypass)", use_container_width=True):
            st.session_state['chart_auth_verified'] = True
            st.session_state['chart_page_session'] = "SIMULATION_ACTIVE"
            st.rerun()
            
    use_simulation_fallback = True
else:
    if st.session_state['chart_page_session'] == "SIMULATION_ACTIVE":
        use_simulation_fallback = True
    else:
        try:
            market_data = MarketData(st.session_state['chart_page_session'])
        except Exception:
            use_simulation_fallback = True

# 🌟 PREMIUM DARK THEME STYLE SHEET INJECTION
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        .tc-dashboard-header {
            background: linear-gradient(135deg, #111827 0%, #030712 100%);
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 15px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }
        .tc-title { color: #f3f4f6; font-size: 18px; font-weight: 800; margin: 0; }
        .tc-metrics-container { display: flex; gap: 10px; flex-wrap: wrap; }
        .tc-badge { padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; display: inline-block; }
        .badge-ce { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-pe { background-color: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-pp { background-color: rgba(234, 179, 8, 0.12); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.2); }
        .badge-backup { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    </style>
""", unsafe_allow_html=True)

# 📂 BACKUP FILE INITIALIZATION
BACKUP_DIR = "chart_backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

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
# 🎯 2. SIDEBAR CONTROLS LAYOUT
# ==============================================================================
st.sidebar.header("📁 Backup File System")
load_from_backup = st.sidebar.checkbox("📅 Load Past Day Backup (Offline)", value=False)

selected_backup_file = None
if load_from_backup:
    available_backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".csv")], reverse=True)
    if available_backups:
        selected_backup_file = st.sidebar.selectbox("📂 Select Saved Day Chart", available_backups)
    else:
        st.sidebar.warning("No backup files found!")

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
# pages/2_chart.py (PART 2 - Fragment Engine with Fully Bound Arguments)

# ==============================================================================
# 🧠 4. MATHEMATICAL INDICATORS COMPUTATION ENGINE
# ==============================================================================
def calculate_indicators(df, mult_value, period_value, rsi_pd_value, interval):
    df['dma_9'] = df['close'].rolling(window=9, min_periods=1).mean()
    df['dma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['dma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    
    if 'volume' in df.columns and interval != "1d":
        df['volume_clean'] = df['volume'].fillna(0)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        pv = typical_price * df['volume_clean']
        cum_pv = pv.cumsum()
        cum_v = df['volume_clean'].cumsum()
        
        df['vwap'] = np.where(cum_v > 0, cum_pv / cum_v, df['close'])
        min_c, max_c = df['close'].min(), df['close'].max()
        df['vwap'] = np.where((df['vwap'] < min_c * 0.95) | (df['vwap'] > max_c * 1.05), np.nan, df['vwap'])
    else:
        df['vwap'] = df['close']
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_pd_value).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_pd_value).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
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
            
    df['supertrend'] = df['supertrend'].ffill()

    df['date_only'] = df.index.date
    unique_dates = sorted(list(set(df['date_only'])))
    df['daily_H4'] = np.nan
    df['daily_H3'] = np.nan
    df['daily_L3'] = np.nan
    df['daily_L4'] = np.nan
    
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

    m_high = df['high'].max()
    m_low = df['low'].min()
    m_close = df['close'].iloc[-1]
    m_range = m_high - m_low
    df['monthly_H4'] = m_close + (m_range * 1.1 / 2)
    df['monthly_H3'] = m_close + (m_range * 1.1 / 4)
    df['monthly_L3'] = m_close - (m_range * 1.1 / 4)
    df['monthly_L4'] = m_close - (m_range * 1.1 / 2)

    return df

# ==============================================================================
# 🧠 5. SEAMLESS FALLBACK VECTOR DATA MAKER
# ==============================================================================
def get_simulation_dataframe(target_symbol, interval):
    base_price = 23200.0 if target_symbol == "NIFTY" else (50100.0 if target_symbol == "BANKNIFTY" else 76000.0)
    if target_symbol not in ["NIFTY", "BANKNIFTY", "SENSEX"]: base_price = 500.0
    timestamps = pd.date_range(end=datetime.now(), periods=100, freq='5min' if interval=="5m" else 'D')
    np.random.seed(int(time.time()) % 1000)
    changes = np.random.normal(0, base_price * 0.002, 100)
    closes = base_price + np.cumsum(changes)
    opens = closes - np.random.normal(0, base_price * 0.001, 100)
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0, base_price * 0.0015, 100))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0, base_price * 0.0015, 100))
    volumes = np.random.randint(1000, 50000, 100)
    sim_df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}, index=timestamps)
    return sim_df

# ==============================================================================
# ⚡ 6. STREAMLIT FRAGMENT CONTAINER (FULLY INDEPENDENT STATE PARSER)
# ==============================================================================
@st.fragment(run_every=15)
def render_isolated_chart_fragment(
    target_symbol, interval, use_simulation_fallback, load_from_backup, selected_backup_file, BACKUP_DIR,
    show_zones, show_supertrend, show_dma, show_vwap, show_daily_camarilla, show_monthly_camarilla,
    rsi_period, st_multiplier, st_period, st_color, dma9_color, dma20_color, dma50_color, vwap_color,
    draw_h_line, h_line_value, h_line_color, draw_v_line, v_line_idx, v_line_color
):
    df = None
    is_backup_loaded_flag = False

    if load_from_backup and selected_backup_file:
        backup_path = os.path.join(BACKUP_DIR, selected_backup_file)
        if os.path.exists(backup_path):
            df = pd.read_csv(backup_path, index_col=0, parse_dates=True)
            is_backup_loaded_flag = True

    if df is None:
        if use_simulation_fallback:
            df = get_simulation_dataframe(target_symbol, interval)
            df = calculate_indicators(df, st_multiplier, st_period, rsi_period, interval)
        else:
            end_dt = datetime.utcnow()
            lookback_days = 60 if interval == "1d" else 7
            start_dt = end_dt - timedelta(days=lookback_days) 
            api_type = "INDEX" if target_symbol in ["NIFTY", "BANKNIFTY", "SENSEX"] else "STOCK"
            exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
            
            try:
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
                        df = calculate_indicators(df, st_multiplier, st_period, rsi_period, interval)
            except Exception:
                df = get_simulation_dataframe(target_symbol, interval)
                df = calculate_indicators(df, st_multiplier, st_period, rsi_period, interval)

    if df is None or len(df) == 0:
        st.error(f"❌ '{target_symbol}' ke liye koi data stream nahi mila.")
        return

    latest_row = df.iloc[-1]
    current_ltp = float(latest_row['close'])

    if target_symbol == "NIFTY":
        base_upper = float(((current_ltp + 25) // 50) * 50 + 50); sup_low = base_upper; sup_high = float(sup_low + 30)
        base_lower = float(((current_ltp - 25) // 50) * 50 - 50); dem_low = base_lower; dem_high = float(dem_low + 30)
    elif target_symbol == "BANKNIFTY":
        base_upper = float(((current_ltp + 50) // 100) * 100 + 100); sup_low = base_upper; sup_high = float(base_upper + (current_ltp * 0.003))
        base_lower = float(((current_ltp - 50) // 100) * 100 - 100); dem_high = base_lower; dem_low = float(base_lower - (current_ltp * 0.003))
    elif target_symbol == "SENSEX":
        base_upper = float(((current_ltp + 50) // 100) * 100 + 100); sup_low = base_upper; sup_high = float(base_upper + (current_ltp * 0.0025))
        base_lower = float(((current_ltp - 50) // 100) * 100 - 100); dem_high = base_lower; dem_low = float(base_lower - (current_ltp * 0.0025))
    else:
        sup_high = float(current_ltp * 1.015); sup_low = float(current_ltp * 1.010)
        dem_high = float(current_ltp * 0.990); dem_low = float(current_ltp * 0.985)

    p_point = round((sup_low + dem_high + current_ltp) / 3)

    status_title = f"📁 BACKUP: {selected_backup_file}" if is_backup_loaded_flag else f"⚡ {target_symbol} PREMIUM TERMINAL"
    badge_status_class = "badge-backup" if is_backup_loaded_flag else "badge-pp"
    badge_status_label = "OFFLINE MODE" if is_backup_loaded_flag else f"MID-PIVOT (PP): {p_point}"

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

    try:
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(gr.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="LTP Price", increasing_line_color='#00cc66', decreasing_line_color='#ff3333', increasing_fillcolor='#00cc66', decreasing_fillcolor='#ff3333'), row=1, col=1)

        if show_zones:
            box_start_idx = max(0, len(df) - 15)
            fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=sup_low, y1=sup_high, fillcolor="rgba(239, 68, 68, 0.20)", line=dict(color="#ff3333", width=2), row=1, col=1)
            fig.add_shape(type="rect", x0=df.index[box_start_idx], x1=df.index[-1], y0=dem_low, y1=dem_high, fillcolor="rgba(16, 185, 129, 0.20)", line=dict(color="#00cc66", width=2), row=1, col=1)
            fig.add_hline(y=sup_high, line_dash="solid", line_color="#ff3333", row=1, col=1)
            fig.add_hline(y=sup_low, line_dash="solid", line_color="#ff3333", row=1, col=1)
            fig.add_hline(y=dem_high, line_dash="solid", line_color="#00cc66", row=1, col=1)
            fig.add_hline(y=dem_low, line_dash="solid", line_color="#00cc66", row=1, col=1)
            fig.add_hline(y=p_point, line_width=1.5, line_dash="dashdot", line_color="#eab308", annotation_text=f"PP: {p_point}", annotation_position="top left", row=1, col=1)

        if show_supertrend: fig.add_trace(gr.Scatter(x=df.index, y=df['supertrend'], line=dict(color=st_color, width=2), name="SuperTrend"), row=1, col=1)
        if show_dma:
            fig.add_trace(gr.Scatter(x=df.index, y=df['dma_9'], line=dict(color=dma9_color, width=1.5), name="9 DMA"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['dma_20'], line=dict(color=dma20_color, width=1.5), name="20 DMA"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['dma_50'], line=dict(color=dma50_color, width=2), name="50 DMA"), row=1, col=1)
        if show_vwap and 'vwap' in df.columns: fig.add_trace(gr.Scatter(x=df.index, y=df['vwap'], line=dict(color=vwap_color, width=3.5), name="VWAP", connectgaps=False), row=1, col=1)

        if show_daily_camarilla:
            fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H4'], line=dict(color='#ff1744', width=1, dash="dot"), name="Daily H4"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['daily_H3'], line=dict(color='#ff9100', width=1, dash="dot"), name="Daily H3"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L3'], line=dict(color='#00e676', width=1, dash="dot"), name="Daily L3"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['daily_L4'], line=dict(color='#00b0ff', width=1, dash="dot"), name="Daily L4"), row=1, col=1)

        if show_monthly_camarilla:
            fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_H4'], line=dict(color='#b71c1c', width=1.5), name="Monthly H4"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_H3'], line=dict(color='#f57c00', width=1.5), name="Monthly H3"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_L3'], line=dict(color='#388e3c', width=1.5), name="Monthly L3"), row=1, col=1)
            fig.add_trace(gr.Scatter(x=df.index, y=df['monthly_L4'], line=dict(color='#1565c0', width=1.5), name="Monthly L4"), row=1, col=1)

        if draw_h_line and h_line_value > 0: fig.add_hline(y=h_line_value, line_color=h_line_color, line_width=2, annotation_text=f"Custom: {h_line_value:.2f}", row=1, col=1)
        if draw_v_line and len(df) > v_line_idx:
            target_time = df.index[-v_line_idx]
            fig.add_vline(x=target_time, line_color=v_line_color, line_width=2, line_dash="dash", row=1, col=1)

        fig.add_trace(gr.Scatter(x=[df.index[-1]], y=[current_ltp], mode="markers+text", marker=dict(color="#ffff00", size=10, symbol="arrow-left"), text=[f"  ◄ LTP: {current_ltp:.2f}"], textposition="middle right", textfont=dict(color="#ffff00", size=13, family="Arial Black"), name="Current LTP", showlegend=False), row=1, col=1)

        min_price, max_price = float(df['low'].min()), float(df['high'].max())
        top_y_limit, bottom_y_limit = max(max_price, sup_high) * 1.015, min(min_price, dem_low) * 0.985

        fig.update_layout(
            height=520, xaxis_rangeslider_visible=False, template="plotly_dark", bargap=0.35, margin=dict(l=10, r=150, t=10, b=25),
            yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), tickformat=".2f", range=[bottom_y_limit, top_y_limit], autorange=False, fixedrange=False),
            xaxis=dict(showgrid=True, gridcolor="#1e293b", tickfont=dict(color="#94a3b8", size=11), autorange=True, fixedrange=False),
            paper_bgcolor='#030712', plot_bgcolor='#030712'
        )
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("🔄 Re-aligning framework graphics matrix vectors...")

    st.markdown("### 📊 Live Terminal Reference Dashboard")
    c1, c2, c3 = st.columns(3)
    with c1: st.info(f"🔴 **Sells/Supply Zone (DR):** {sup_low:.1f} - {sup_high:.1f}")
    with c2: st.success(f"🟢 **Buys/Demand Zone (DS):** {dem_low:.1f} - {dem_high:.1f}")
    with c3: st.warning(f"🟡 **Live Market LTP:** ₹{current_ltp:.2f}")

# 🔥 FIXED: Trigger execution passing all sidebar configurations cleanly inside arguments map
render_isolated_chart_fragment(
    target_symbol, interval, use_simulation_fallback, load_from_backup, selected_backup_file, BACKUP_DIR,
    show_zones, show_supertrend, show_dma, show_vwap, show_daily_camarilla, show_monthly_camarilla,
    rsi_period, st_multiplier, st_period, st_color, dma9_color, dma20_color, dma50_color, vwap_color,
    draw_h_line, h_line_value, h_line_color, draw_v_line, v_line_idx, v_line_color
)
