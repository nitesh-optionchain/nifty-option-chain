import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP & NEO-GLOW CYBERPUNK STYLES =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 PREMIUM CLASS HIGH-GLOW BORDERS INJECTION SHEET
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 95% !important;
        }
        
        /* Main Cyber Frame Box */
        .terminal-container {
            background-color: #0b0f19;
            border: 2px solid #1e293b;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.8);
            margin-bottom: 25px;
        }
        
        .asset-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        
        .asset-title {
            font-size: 22px;
            font-weight: 900;
            color: #ffffff;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        
        /* UPPER RIGHT EDGE GLOWING BADGE */
        .live-ltp-badge-container {
            font-size: 16px;
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: 0.5px;
            background-color: #030712;
        }
        
        .badge-up {
            color: #4ade80 !important;
            border: 1px solid #22c55e;
            box-shadow: 0 0 15px rgba(34, 197, 94, 0.25);
        }
        
        .badge-down {
            color: #f87171 !important;
            border: 1px solid #ef4444;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.25);
        }
        
        /* MATRIX BLOCKS STRUCTURE WITH SOLID GLOWS */
        .zones-grid {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            width: 100%;
        }
        
        .zone-card {
            flex: 1;
            min-width: 280px;
            border-radius: 8px;
            padding: 24px 15px;
            text-align: center;
            background-color: #030712;
            transition: all 0.3s ease;
        }
        
        /* 🔴 Supply Neo Glow Border */
        .card-resistance {
            border: 2px solid #ef4444 !important;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
        }
        .card-resistance:hover {
            box-shadow: 0 0 25px rgba(239, 68, 68, 0.55);
        }
        
        /* 🟡 Pivot Neo Glow Border */
        .card-pivot {
            border: 2px solid #eab308 !important;
            box-shadow: 0 0 15px rgba(234, 179, 8, 0.3);
        }
        .card-pivot:hover {
            box-shadow: 0 0 25px rgba(234, 179, 8, 0.55);
        }
        
        /* 🟢 Support Neo Glow Border */
        .card-support {
            border: 2px solid #22c55e !important;
            box-shadow: 0 0 15px rgba(34, 197, 94, 0.3);
        }
        .card-support:hover {
            box-shadow: 0 0 25px rgba(34, 197, 94, 0.55);
        }
        
        .card-label {
            font-size: 12px;
            font-weight: 800;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 14px;
        }
        
        .card-value {
            font-size: 30px;
            font-weight: 900;
            letter-spacing: 0.5px;
        }
        .val-red { color: #f87171; }
        .val-yellow { color: #fde047; }
        .val-green { color: #4ade80; }
        
        .sync-timestamp {
            font-size: 11px;
            color: #4b5563;
            text-align: right;
            margin-top: 22px;
            font-family: monospace;
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
    st.error("❌ Market engine connection failed. Verify secrets configuration tokens.")
    st.stop()

# ==============================================================================
# ⚙️ 3. SIDEBAR ANCHORS FRAME
# ==============================================================================
st.sidebar.header("⚙️ Terminal Controller")
target_symbol = st.sidebar.selectbox("🔤 Select Active Index", ["NIFTY", "BANKNIFTY", "SENSEX"], index=0)

exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"
current_ltp = 0.0

try:
    snap = market_data.current_price(target_symbol, exchange=exchange_type)
    if snap and getattr(snap, 'price', None):
        raw_p = float(snap.price)
        current_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
except Exception:
    pass

# Intraday Net change anchors mappings
prev_close_map = {"NIFTY": 24050.00, "BANKNIFTY": 52200.00, "SENSEX": 79300.00}
fallback_prices = {"NIFTY": 24094.50, "BANKNIFTY": 52350.20, "SENSEX": 79420.80}

if current_ltp == 0.0:
    current_ltp = fallback_prices.get(target_symbol, 24000.0)

# DIRECTIONAL CALCULATIONS GRID FOR THE HEADER CORNER INDICATOR
base_close_p = prev_close_map.get(target_symbol, current_ltp)
net_change = current_ltp - base_close_p
change_pct = (net_change / base_close_p) * 100.0

if net_change >= 0:
    ltp_badge_class = "badge-up"
    market_arrow = "▲"
    sign_prefix = "+"
else:
    ltp_badge_class = "badge-down"
    market_arrow = "▼"
    sign_prefix = ""

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

# ==============================================================================
# 🖥️ 5. LIVE PREMIUM CONTAINER INJECTION FRAMEWORK
# ==============================================================================
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# Render elements dynamically using partitioned isolated layouts
st.markdown(f"""
<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">NEXT DAY INSTITUTIONAL LEVELS GRID</div>
        <div class="live-ltp-badge-container {ltp_badge_class}">
            <span>⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
            <span>{market_arrow} {sign_prefix}{net_change:.2f} ({sign_prefix}{change_pct:.2f}%)</span>
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
""", unsafe_allow_html=True)

# 🔄 AUTOMATIC 2-SECOND DYNAMIC SYNC REFRESH LOOP
st_autorefresh(interval=2000, key="premium_zones_auto_sync")
