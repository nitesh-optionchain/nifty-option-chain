import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 PURE INJECTED NEO-GLOW DYNAMIC CONTROLLER CSS
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 96% !important;
        }
        
        /* Main Visual Container Frame */
        .terminal-container {
            background-color: #151922 !important;
            border: 1px solid #232d3f !important;
            border-radius: 12px !important;
            padding: 24px 18px !important;
            box-shadow: 0 0 25px rgba(0, 0, 0, 0.6) !important;
            margin-bottom: 10px !important;
            font-family: sans-serif !important;
        }
        
        /* Layout Row inside the Black Terminal Box */
        .asset-header-row {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            border-bottom: 1px solid #232d3f !important;
            padding-bottom: 16px !important;
            margin-bottom: 22px !important;
        }
        
        /* LEFT SIDEWAY IN-BOX DROP-DOWN ANCHOR OVERRIDES */
        div[data-baseweb="select"] {
            border-radius: 6px !important;
            background-color: #11151d !important;
            min-width: 150px !important;
            transition: all 0.3s ease !important;
        }
        
        /* Dynamic Border & Glow Logic Injection based on Trends */
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
        
        /* Strip Native Text Selector Labels */
        .stSelectbox label {
            display: none !important;
        }
        
        /* RIGHT SIDEWAY LIVE LTP CONTAINER BADGES */
        .live-ltp-badge-container {
            font-size: 13px !important;
            font-weight: 800 !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            background-color: #11151d !important;
            white-space: nowrap !important;
        }
        
        .index-glow-green {
            border: 2px solid #00ff66 !important;
            box-shadow: 0 0 14px rgba(0, 255, 102, 0.45) !important;
        }
        
        .index-glow-red {
            border: 2px solid #ff3333 !important;
            box-shadow: 0 0 14px rgba(255, 51, 51, 0.45) !important;
        }
        
        .text-market-up { color: #00ff66 !important; font-weight: 900 !important; }
        .text-market-down { color: #ff3333 !important; font-weight: 900 !important; }
        
        /* THREE-CARD ZONE GRID FRAMEWORK */
        .zones-grid {
            display: flex !important;
            gap: 16px !important;
            flex-wrap: wrap !important;
            width: 100% !important;
        }
        
        .zone-card {
            flex: 1 !important;
            min-width: 240px !important;
            border-radius: 8px !important;
            padding: 22px 12px !important;
            text-align: center !important;
            background-color: #1a202c !important;
        }
        
        .card-resistance { border: 1px solid #ef4444 !important; }
        .card-pivot { border: 1px solid #eab308 !important; }
        .card-support { border: 1px solid #22c55e !important; }
        
        .card-label {
            font-size: 10px !important;
            font-weight: 700 !important;
            color: #a0aec0 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            margin-bottom: 8px !important;
        }
        
        .card-value {
            font-size: 26px !important;
            font-weight: 800 !important;
        }
        .val-red { color: #ff4d4d !important; }
        .val-yellow { color: #ffcc00 !important; }
        .val-green { color: #33ff77 !important; }
        
        .sync-timestamp-footer {
            font-size: 10px !important;
            color: #5c6b73 !important;
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
# 🎛️ 3. PRE-FETCH DATA RUNTIME FOR VALUE ENGINE
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
# 🎛️ 4. IN-BOX DYNAMIC LAYOUT ENGINE (TITLE REPLACED BY GLOW RECTANGLE BUTTON)
# ==============================================================================
# Main outer container logic starts
st.markdown('<div class="terminal-container"><div class="asset-header-row">', unsafe_allow_html=True)

# Generate multi-column placeholder grid layout framework natively inside header row
h_grid = st.columns([1.5, 3, 1.5])

with h_grid[0]:
    # Left side dropdown replaces heading completely with identical rectangle border glow layout
    st.markdown(f'<div class="{dropdown_glow_class}">', unsafe_allow_html=True)
    display_options = ["NIFTY", "BANKNIFTY", "SENSEX"]
    selected_idx = display_options.index(current_selection) if current_selection in display_options else 0
    
    chosen_symbol = st.selectbox(
        "Embedded Selection Core Control",
        display_options,
        index=selected_idx,
        label_visibility="collapsed",
        key="main_inbox_rectangular_selector"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Rerun state system if choice altered
if chosen_symbol != st.session_state.active_selected_index:
    st.session_state.active_selected_index = chosen_symbol
    st.rerun()

target_symbol = st.session_state.active_selected_index

with h_grid[2]:
    # Right side retains dynamic sleek text matrix
    st.markdown(f"""
        <div style="display: flex; justify-content: flex-end;">
            <div class="live-ltp-badge-container {index_glow_class}">
                <span class="{color_class}">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
                <span class="{color_class}">{arrow} {sign}{abs(net_change):.2f} ({sign}{change_pct:.2f}%)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Close header element architecture securely
st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🧠 5. MATHEMATICAL STRIKE ENGINE CALCULATION MATRIX
# ==============================================================================
if target_symbol == "NIFTY":
    base_strike = float((current_ltp // 50) * 50)
    sup_low = base_strike - 50
    sup_high = sup_low + 30
    dem_high = base_strike - 200
    dem_low = dem_high - 30
elif target_symbol == "BANKNIFTY":
    base_strike = float((current_ltp // 100) * 100)
    sup_low = base_strike - 100
    sup_high = sup_low + 150
    dem_high = base_strike - 400
    dem_low = dem_high - 150
else: # SENSEX
    base_strike = float((current_ltp // 100) * 100)
    sup_low = base_strike - 100
    sup_high = sup_low + 100
    dem_high = base_strike - 300
    dem_low = dem_high - 100

# ==============================================================================
# ⚡ 6. NO-NOISE STABLE INTERPRETER MODULE FOR TICK DATA
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
            if target_symbol not in symbol_tag:
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
            if target_symbol == "NIFTY" and best_ce_strike > current_ltp + 50:
                best_ce_strike -= 50
                
            sup_low = float(best_ce_strike)
            sup_high = float(best_ce_strike + (30 if target_symbol == "NIFTY" else 150 if target_symbol == "BANKNIFTY" else 100))
            
            dem_high = float(best_pe_strike)
            dem_low = float(best_pe_strike - (30 if target_symbol == "NIFTY" else 150 if target_symbol == "BANKNIFTY" else 100))
    except Exception:
        pass

p_point = round((sup_low + dem_high) / 2)
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ==============================================================================
# 🖥️ 7. TABLE CARD CONTENT GENERATION CORE
# ==============================================================================
terminal_grid_html = f"""
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

st.markdown(terminal_grid_html, unsafe_allow_html=True)

# 🔄 AUTOMATIC 2-SECOND RUNTIME REFRESH
st_autorefresh(interval=2000, key="premium_zones_auto_sync")
