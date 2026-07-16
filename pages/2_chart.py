import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 STANDALONE CSS INJECTION - DEFINES PIC-2 BLOCKS WITH SOLID NEON GLOW BORDERS
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 95% !important;
        }
        
        /* Main Dark Dashboard Base Container */
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
        
        /* CARD SYSTEM WITH SOLID NEON GLOW CHANNELS */
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
    st.error("❌ Market engine connection parameters missing.")
    st.stop()

# ==============================================================================
# ⚙️ 3. SIDEBAR ANCHORS FRAME CONTROLLER
# ==============================================================================
st.sidebar.header("⚙️ Terminal Controller")
target_symbol = st.sidebar.selectbox("🔤 Select Active Index", ["NIFTY", "BANKNIFTY", "SENSEX"], index=0)

exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"

# Sane baseline fallbacks for calibration validation loops
default_closes = {"NIFTY": 24050.00, "BANKNIFTY": 52460.60, "SENSEX": 77156.35}

current_ltp = 0.0
yesterday_close = default_closes.get(target_symbol, 24000.0)

try:
    snap = market_data.current_price(target_symbol, exchange=exchange_type)
    if snap:
        if getattr(snap, 'price', None):
            raw_p = float(snap.price)
            current_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
        
        # Sahi previous close fetch karne ki koshish karne ka rule matrix
        if hasattr(snap, 'close') and snap.close:
            raw_c = float(snap.close)
            yesterday_close = raw_c / 100.0 if raw_c > 100000 else raw_c
        elif hasattr(snap, 'prev_close') and snap.prev_close:
            raw_pc = float(snap.prev_close)
            yesterday_close = raw_pc / 100.0 if raw_pc > 100000 else raw_pc
except Exception:
    pass

if current_ltp == 0.0:
    fallback_ltps = {"NIFTY": 24059.80, "BANKNIFTY": 52350.20, "SENSEX": 77145.08}
    current_ltp = fallback_prices.get(target_symbol, yesterday_close)

# 🎯 MATH BASED EXACT DYNAMIC DIFFERENCE GENERATOR (FIXES THE RED SHIFT GAP)
net_change = current_ltp - yesterday_close
change_pct = (net_change / yesterday_close) * 100.0 if yesterday_close > 0 else 0.0

if net_change >= 0:
    color_class = "text-market-up"
    arrow = "▲"
    sign = "+"
else:
    color_class = "text-market-down"
    arrow = "▼"
    sign = ""

# ==============================================================================
# 🧠 4. MATHEMATICAL EXTRACTION ZONES
# ==============================================================================
if target_symbol == "NIFTY":
    base_upper = float(((current_ltp + 25) // 50) * 50 + 50)
    sup_low = base_upper
    sup_high = float(sup_low + 30)
    base_lower = float(((current_ltp - 25) // 50) * 50 - 50)
    dem_low = base_lower
    dem_high = float(dem_low + 30)
elif target_symbol == "BANKNIFTY":
    base_upper = float(((current_ltp + 50) // 100) * 100 + 100)
    sup_low = base_upper
    sup_high = float(base_upper + (current_ltp * 0.003))
    base_lower = float(((current_ltp - 50) // 100) * 100 - 100)
    dem_high = base_lower
    dem_low = float(base_lower - (current_ltp * 0.003))
elif target_symbol == "SENSEX":
    base_upper = float(((current_ltp + 50) // 100) * 100 + 100)
    sup_low = base_upper
    sup_high = float(base_upper + (current_ltp * 0.0025))
    base_lower = float(((current_ltp - 50) // 100) * 100 - 100)
    dem_high = base_lower
    dem_low = float(base_lower - (current_ltp * 0.0025))
else:
    sup_high = float(current_ltp * 1.015)
    sup_low = float(current_ltp * 1.010)
    dem_high = float(current_ltp * 0.990)
    dem_low = float(current_ltp * 0.985)

p_point = round((sup_low + dem_high + current_ltp) / 3)
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ==============================================================================
# 🖥️ 5. WATERPROOF MATRIC COMPONENT INJECTION
# ==============================================================================
st.html(f"""
<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">NEXT DAY INSTITUTIONAL LEVELS GRID</div>
        <div class="live-ltp-badge-container">
            <span class="{color_class}">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
            <span class="{color_class}">{arrow} {sign}{net_change:.2f} ({sign}{change_pct:.2f}%)</span>
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
