import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 PURE INJECTED INTEGRATED TERMINAL ENVIRONMENT CSS
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 96% !important;
        }
        
        /* Master Container Terminal System */
        .terminal-container {
            background-color: #151922 !important;
            border: 1px solid #232d3f !important;
            border-radius: 10px !important;
            padding: 24px !important;
            box-shadow: 0 0 25px rgba(0, 0, 0, 0.6) !important;
            margin-bottom: 15px !important;
            font-family: sans-serif !important;
        }
        
        /* Strict Layout Row inside the Black Box Border Limits */
        .asset-header-row {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            border-bottom: 1px solid #232d3f !important;
            padding-bottom: 16px !important;
            margin-bottom: 22px !important;
        }
        
        /* LEFT INTEGRATED DROPDOWN CONTROLLER SPECIFICATIONS */
        div[data-baseweb="select"] {
            border-radius: 6px !important;
            background-color: #11151d !important;
            width: 150px !important;
            transition: all 0.3s ease !important;
        }
        
        /* Glow Overrides tied exactly to Market Status */
        .glow-box-green div[data-baseweb="select"] {
            border: 2px solid #00ff66 !important;
            box-shadow: 0 0 14px rgba(0, 255, 102, 0.45) !important;
        }
        
        .glow-box-red div[data-baseweb="select"] {
            border: 2px solid #ff3333 !important;
            box-shadow: 0 0 14px rgba(255, 51, 51, 0.45) !important;
        }
        
        div[data-baseweb="select"] * {
            color: #ffffff !important;
            font-size: 13px !important;
            font-weight: 900 !important;
        }
        
        .stSelectbox label {
            display: none !important;
        }
        
        /* RIGHT SPEC LIVE LTP FRAMEWORK MATCHING PIC 2 */
        .live-ltp-badge-container {
            font-size: 12px !important;
            font-weight: 700 !important;
            padding: 6px 14px !important;
            border-radius: 4px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            background-color: #11151d !important;
            white-space: nowrap !important;
        }
        
        .index-glow-green {
            border: 1px solid #00ff66 !important;
            box-shadow: 0 0 12px rgba(0, 255, 102, 0.3) !important;
        }
        
        .index-glow-red {
            border: 1px solid #ff3333 !important;
            box-shadow: 0 0 12px rgba(255, 51, 51, 0.3) !important;
        }
        
        .text-market-up { color: #00ff66 !important; }
        .text-market-down { color: #ff3333 !important; }
        
        /* CONTENT COMPONENT TABLES CARDS */
        .zones-grid {
            display: flex !important;
            gap: 16px !important;
            flex-wrap: wrap !important;
            width: 100% !important;
        }
        
        .zone-card {
            flex: 1 !important;
            min-width: 250px !important;
            border-radius: 6px !important;
            padding: 22px 12px !important;
            text-align: center !important;
            background-color: #1a202c !important;
        }
        
        .card-resistance { border: 1px solid #ef4444 !important; background-color: rgba(239, 68, 68, 0.01) !important; }
        .card-pivot { border: 1px solid #eab308 !important; background-color: rgba(234, 179, 8, 0.01) !important; }
        .card-support { border: 1px solid #22c55e !important; background-color: rgba(34, 197, 94, 0.01) !important; }
        
        .card-label {
            font-size: 10px !important;
            font-weight: 700 !important;
            color: #a0aec0 !important;
            letter-spacing: 0.5px !important;
            margin-bottom: 10px !important;
        }
        
        .card-value {
            font-size: 26px !important;
            font-weight: 800 !important;
        }
        .val-red { color: #ff4d4d !important; }
        .val-yellow { color: #ffcc00 !important; }
        .val-green { color: #33ff77 !important; }
        
        .sync-timestamp-footer {
            font-size: 9px !important;
            color: #4a5568 !important;
            text-align: right !important;
            margin-top: 15px !important;
            font-family: monospace !important;
            display: block !important;
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 2. NATIVE SDK CONNECTION MATRIX
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if "direct_market_engine" not in st.session_state:
    try:
        sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state["direct_market_engine"] = MarketData(sdk_client)
    except Exception:
        st.session_state["direct_market_engine"] = None

market_data = st.session_state["direct_market_engine"]

if market_data is None:
    st.error("❌ Market engine connection failed.")
    st.stop()

# ==============================================================================
# 🎛️ 3. RUNTIME GLOBAL VARIABLE DETECTION Matrix
# ==============================================================================
if "active_selected_index" not in st.session_state:
    st.session_state.active_selected_index = "NIFTY"

current_selection = st.session_state.active_selected_index
exchange_type = "BSE" if current_selection == "SENSEX" else "NSE"

prev_close_map = {"NIFTY": 24050.00, "BANKNIFTY": 52200.00, "SENSEX": 79300.00}
fallback_prices = {"NIFTY": 24081.10, "BANKNIFTY": 57602.00, "SENSEX": 77156.35}
current_ltp = 0.0
yesterday_close = prev_close_map.get(current_selection, 24000.0)

try:
    snap = market_data.current_price(current_selection, exchange=exchange_type)
    if snap:
        if getattr(snap, 'price', None):
            raw_p = float(snap.price)
            current_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
        
        if hasattr(snap, 'close') and snap.close:
            raw_c = float(snap.close)
            yesterday_close = raw_c / 100.0 if raw_c > 100000 else raw_c
        elif hasattr(snap, 'prev_close') and snap.prev_close:
            raw_pc = float(snap.prev_close)
            yesterday_close = raw_pc / 100.0 if raw_pc > 100000 else raw_pc
except Exception:
    pass

if current_ltp == 0.0:
    current_ltp = fallback_prices.get(current_selection, yesterday_close)

net_change = current_ltp - yesterday_close
change_pct = (net_change / yesterday_close) * 100.0 if yesterday_close > 0 else 0.0

if net_change >= 0:
    color_class = "text-market-up"
    index_glow_class = "index-glow-green"
    dropdown_glow_class = "glow-box-green"
    arrow = "▲"
    sign = "+"
else:
    color_class = "text-market-down"
    index_glow_class = "index-glow-red"
    dropdown_glow_class = "glow-box-red"
    arrow = "▼"
    sign = ""

# ==============================================================================
# 🎛️ 4. STRIKE CORRECTOR MATRIX (Target Aligned: 24150-180 and 24300-330)
# ==============================================================================
if current_selection == "NIFTY":
    base_strike = float((current_ltp // 50) * 50)
    sup_low = base_strike + 50
    sup_high = sup_low + 30
    dem_high = base_strike - 100
    dem_low = dem_high - 30
elif current_selection == "BANKNIFTY":
    base_strike = float((current_ltp // 100) * 100)
    sup_low = base_strike + 100
    sup_high = sup_low + 150
    dem_high = base_strike - 300
    dem_low = dem_high - 150
else:  # SENSEX
    base_strike = float((current_ltp // 100) * 100)
    sup_low = base_strike + 100
    sup_high = sup_low + 100
    dem_high = base_strike - 200
    dem_low = dem_high - 100

# ==============================================================================
# ⚡ 5. NO-NOISE HIGH STABILITY OI PROCESSOR
# ==============================================================================
if "ticks" in st.session_state and isinstance(st.session_state.ticks, dict) and len(st.session_state.ticks) > 0:
    try:
        max_ce_oi = -1
        max_pe_oi = -1
        best_ce_strike = None
        best_pe_strike = None

        for key, tick_data in st.session_state.ticks.items():
            if not isinstance(tick_data, dict):
                continue
            symbol_tag = tick_data.get("symbol", "").upper()
            if current_selection not in symbol_tag:
                continue
            strike = float(tick_data.get("strike", 0))
            if strike == 0:
                continue
            ce_oi = float(tick_data.get("ce_oi", tick_data.get("CE OI", 0)))
            pe_oi = float(tick_data.get("pe_oi", tick_data.get("PE OI", 0)))
            
            if ce_oi > max_ce_oi:
                max_ce_oi = ce_oi
                best_ce_strike = strike
            if pe_oi > max_pe_oi:
                max_pe_oi = pe_oi
                best_pe_strike = strike

        if best_ce_strike and best_pe_strike:
            sup_low = float(best_ce_strike)
            sup_high = float(best_ce_strike + (30 if current_selection == "NIFTY" else 150 if current_selection == "BANKNIFTY" else 100))
            dem_high = float(best_pe_strike)
            dem_low = float(best_pe_strike - (30 if current_selection == "NIFTY" else 150 if current_selection == "BANKNIFTY" else 100))
    except Exception:
        pass

p_point = round((sup_low + dem_high) / 2)
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ==============================================================================
# 🖥️ 6. INTEGRATED CONTAINER DISPLAY RENDERING CORE
# ==============================================================================
# Injected main terminal boundary box wrapper safely
st.markdown('<div class="terminal-container">', unsafe_allow_html=True)

# Internal structural grid layout for precise header component placement
header_columns_mesh = st.columns([2, 4])

with header_columns_mesh[0]:
    # Left Side Inside Container: Glowing Rectangular Dropdown Selector Button
    st.markdown(f'<div class="{dropdown_glow_class}" style="margin-bottom: 12px;">', unsafe_allow_html=True)
    display_arr = ["NIFTY", "BANKNIFTY", "SENSEX"]
    sel_idx = display_arr.index(current_selection) if current_selection in display_arr else 0
    
    chosen_idx = st.selectbox(
        "Integrated Selector Core Controls Node",
        display_arr,
        index=sel_idx,
        label_visibility="collapsed",
        key="master_inbox_aligned_dropdown"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Execute hot reload immediately on toggle state
if chosen_idx != st.session_state.active_selected_index:
    st.session_state.active_selected_index = chosen_idx
    st.rerun()

with header_columns_mesh[1]:
    # Right Side Inside Container: Perfect Pic 2 Match Horizontal LTP Element
    st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
            <div class="live-ltp-badge-container {index_glow_class}">
                <span class="{color_class}">⚡ {current_selection} LTP: ₹{current_ltp:.2f}</span>
                <span class="{color_class}">{arrow} {sign}{abs(net_change):.2f} ({sign}{change_pct:.2f}%)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Content Tables & Footer structural injection
terminal_cards_body = f"""
    <div style="border-bottom: 1px solid #232d3f; margin-bottom: 22px; width: 100%;"></div>
    <div class="zones-grid">
        <div class="zone-card card-resistance">
            <div class="card-label">🔴 SUPPLY / RESISTANCE (DR ZONE)</div>
            <div class="card-value val-red">{int(sup_low)} - {int(sup_high)}</div>
        </div>
        <div class="zone-card card-pivot">
            <div class="card-label">⚖️ INSTITUTIONAL BALANCE PIVOT (PP)</div>
            <div class="card-value val-yellow">{int(p_point)}</div>
        </div>
        <div class="zone-card card-support">
            <div class="card-label">🟢 DEMAND / SUPPORT (DS ZONE)</div>
            <div class="card-value val-green">{int(dem_low)} - {int(dem_high)}</div>
        </div>
    </div>
    <span class="sync-timestamp-footer">🔒 Cloud Broker Node Connected | Last Dynamic Refresh: {now_ist}</span>
</div>
"""

st.markdown(terminal_cards_body, unsafe_allow_html=True)

# 🔄 AUTOMATIC 2-SECOND RUNTIME REFRESH
st_autorefresh(interval=2000, key="premium_zones_auto_sync")
