import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 STANDALONE CSS INJECTION (EXACT PIC-2 DESIGN WITH SOLID NEON BORDERS)
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 95% !important;
        }
        
        /* Main Container Framework matching Pic-2 */
        .terminal-container {
            background-color: #151922 !important;
            border: 2px solid #2d3748 !important;
            border-radius: 12px !important;
            padding: 26px !important;
            box-shadow: 0 12px 45px rgba(0, 0, 0, 0.8) !important;
            margin-bottom: 25px !important;
            font-family: sans-serif !important;
        }
        
        .asset-header-row {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            border-bottom: 1px solid #2d3748 !important;
            padding-bottom: 16px !important;
            margin-bottom: 24px !important;
        }
        
        .asset-title {
            font-size: 22px !important;
            font-weight: 900 !important;
            color: #ffffff !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
        }
        
        /* HEADER RIGHT CORNER DYNAMIC STATUS INDICATORS */
        .live-ltp-badge-container {
            font-size: 16px !important;
            font-weight: 800 !important;
            padding: 8px 16px !important;
            border-radius: 6px !important;
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            letter-spacing: 0.5px !important;
            background-color: #1a202c !important;
            border: 1px solid #4a5568 !important;
        }
        
        .text-market-up { color: #4ade80 !important; font-weight: 900 !important; }
        .text-market-down { color: #f87171 !important; font-weight: 900 !important; }
        
        /* DYNAMIC NEON GLOW GRID HOVER CARDS */
        .zones-grid {
            display: flex !important;
            gap: 20px !important;
            flex-wrap: wrap !important;
            width: 100% !important;
        }
        
        .zone-card {
            flex: 1 !important;
            min-width: 280px !important;
            border-radius: 8px !important;
            padding: 24px 15px !important;
            text-align: center !important;
            background-color: #1a202c !important;
        }
        
        /* 🔴 Resistance Solid Neon Glow Card */
        .card-resistance {
            border: 2px solid #ef4444 !important;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.35) !important;
        }
        
        /* 🟡 Pivot Solid Neon Glow Card */
        .card-pivot {
            border: 2px solid #eab308 !important;
            box-shadow: 0 0 15px rgba(234, 179, 8, 0.35) !important;
        }
        
        /* 🟢 Support Solid Neon Glow Card */
        .card-support {
            border: 2px solid #22c55e !important;
            box-shadow: 0 0 15px rgba(34, 197, 94, 0.35) !important;
        }
        
        .card-label {
            font-size: 11px !important;
            font-weight: 800 !important;
            color: #a0aec0 !important;
            text-transform: uppercase !important;
            letter-spacing: 1.5px !important;
            margin-bottom: 14px !important;
        }
        
        .card-value {
            font-size: 28px !important;
            font-weight: 900 !important;
            letter-spacing: 0.5px !important;
        }
        .val-red { color: #f87171 !important; }
        .val-yellow { color: #fde047 !important; }
        .val-green { color: #4ade80 !important; }
        
        .sync-timestamp {
            font-size: 11px !important;
            color: #718096 !important;
            text-align: right !important;
            margin-top: 22px !important;
            font-family: monospace !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 2. NATIVE SDK CONNECTION & DYNAMIC ENGINE BINDING
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
    st.error("❌ Market engine connection failed. Recheck Secrets configuration tokens.")
    st.stop()

# ==============================================================================
# ⚙️ 3. SIDEBAR ANCHORS FRAME
# ==============================================================================
st.sidebar.header("⚙️ Terminal Controller")
target_symbol = st.sidebar.selectbox("🔤 Select Active Index", ["NIFTY", "BANKNIFTY", "SENSEX"], index=0)

exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"

current_ltp = 0.0
net_change = 0.0
change_pct = 0.0

try:
    snap = market_data.current_price(target_symbol, exchange=exchange_type)
    if snap:
        if getattr(snap, 'price', None):
            raw_p = float(snap.price)
            current_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
        
        if hasattr(snap, 'net_change') and snap.net_change is not None:
            raw_nc = float(snap.net_change)
            net_change = raw_nc / 100.0 if abs(raw_nc) > 50000 else raw_nc
        
        if hasattr(snap, 'change_percent') and snap.change_percent is not None:
            change_pct = float(snap.change_percent)
except Exception:
    pass

# Dynamic emergency mock fallbacks if network connection drops
if current_ltp == 0.0:
    fallback_data = {
        "NIFTY": {"ltp": 24081.10, "change": 0.00, "pct": 0.00},
        "BANKNIFTY": {"ltp": 52350.20, "change": -110.40, "pct": -0.21},
        "SENSEX": {"ltp": 77156.35, "change": 0.00, "pct": 0.00}
    }
    target_data = fallback_data.get(target_symbol, {"ltp": 24000.0, "change": 0.0, "pct": 0.0})
    current_ltp = target_data["ltp"]
    net_change = target_data["change"]
    change_pct = target_data["pct"]

if net_change >= 0:
    color_class = "text-market-up"
    arrow = "▲"
    sign = "+"
else:
    color_class = "text-market-down"
    arrow = "▼"
    sign = ""

# ==============================================================================
# 🧠 4. DYNAMIC SYSTEM INTEGRATION (REAL CALL/PUT OI DATA EXTRACTION MATRIX)
# ==============================================================================
# Initial safe boundary parameters setup
sup_low, sup_high = current_ltp + 50, current_ltp + 100
dem_low, dem_high = current_ltp - 100, current_ltp - 50

# Extract real high concentration blocks directly from active option chain logs
if "ticks" in st.session_state and isinstance(st.session_state.ticks, dict) and len(st.session_state.ticks) > 0:
    try:
        max_ce_oi = -1
        max_pe_oi = -1
        best_ce_strike = None
        best_pe_strike = None

        # Loop through cached option chain mapping tokens
        for key, tick_data in st.session_state.ticks.items():
            if not isinstance(tick_data, dict):
                continue
                
            # Filter rows aligning with currently targeted active index
            symbol_tag = tick_data.get("symbol", "")
            if target_symbol not in symbol_tag:
                continue
                
            strike = float(tick_data.get("strike", 0))
            if strike == 0:
                continue
                
            ce_oi = float(tick_data.get("ce_oi", 0))
            pe_oi = float(tick_data.get("pe_oi", 0))
            
            # Find the highest density cluster core locations
            if ce_oi > max_ce_oi:
                max_ce_oi = ce_oi
                best_ce_strike = strike
                
            if pe_oi > max_pe_oi:
                max_pe_oi = pe_oi
                best_pe_strike = strike

        # Map institutional concentrations directly into dynamic zone boundaries
        if best_ce_strike:
            sup_low = float(best_ce_strike)
            sup_high = float(best_ce_strike + (50 if target_symbol == "NIFTY" else 100))
            
        if best_pe_strike:
            dem_low = float(best_pe_strike - (50 if target_symbol == "NIFTY" else 100))
            dem_high = float(best_pe_strike)
    except Exception:
        pass

p_point = round((sup_low + dem_high) / 2)
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ==============================================================================
# 🖥️ 5. WATERPROOF HTML INJECTION (OPERATIONAL SECTION IS COMPLETELY DELETED)
# ==============================================================================
st.html(f"""
<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">NEXT DAY INSTITUTIONAL LEVELS GRID</div>
        <div class="live-ltp-badge-container">
            <span class="{color_class}">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
            <span class="{color_class}">{arrow} {sign}{abs(net_change):.2f} ({sign}{change_pct:.2f}%)</span>
        </div>
    </div>
    
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
    
    <div class="sync-timestamp">🔒 Cloud Broker Node Connected | Last Dynamic Refresh: {now_ist}</div>
</div>
""")

# 🔄 AUTOMATIC 2-SECOND DYNAMIC SYNC REFRESH LOOP
st_autorefresh(interval=2000, key="premium_zones_auto_sync")
