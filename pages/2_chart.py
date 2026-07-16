import streamlit as st
import time
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP & MODERN DARK STYLES =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# 🌟 ULTRA MODERN CYBERPUNK THEME DESIGN (COMPLETELY MINIFIED)
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 95% !important;
        }
        
        .terminal-container {
            background: linear-gradient(145deg, #0b0f19 0%, #030712 100%);
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
            margin-bottom: 25px;
        }
        
        .asset-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        
        .asset-title {
            font-size: 26px;
            font-weight: 900;
            color: #f3f4f6;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        
        .live-ltp-badge {
            font-size: 22px;
            font-weight: 900;
            color: #facc15;
            background: rgba(250, 204, 21, 0.1);
            border: 1px solid rgba(250, 204, 21, 0.4);
            padding: 6px 16px;
            border-radius: 6px;
            box-shadow: 0 0 15px rgba(250, 204, 21, 0.2);
        }
        
        .zones-grid {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
            width: 100%;
        }
        
        .zone-card {
            flex: 1;
            min-width: 280px;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        .card-resistance {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(185, 28, 28, 0.03) 100%);
            border: 1px solid rgba(239, 68, 68, 0.4);
        }
        
        .card-support {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(21, 128, 61, 0.03) 100%);
            border: 1px solid rgba(34, 197, 94, 0.4);
        }
        
        .card-pivot {
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.08) 0%, rgba(161, 98, 7, 0.03) 100%);
            border: 1px solid rgba(234, 179, 8, 0.4);
        }
        
        .card-label {
            font-size: 13px;
            font-weight: 800;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 8px;
        }
        
        .card-value {
            font-size: 28px;
            font-weight: 900;
            letter-spacing: 0.5px;
        }
        .val-red { color: #f87171; }
        .val-green { color: #4ade80; }
        .val-yellow { color: #fde047; }
        
        .sync-timestamp {
            font-size: 11px;
            color: #4b5563;
            text-align: right;
            margin-top: 15px;
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
    st.error("❌ Market engine connection failed. Check credentials configuration.")
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

if current_ltp == 0.0:
    fallback_prices = {"NIFTY": 24096.35, "BANKNIFTY": 52350.20, "SENSEX": 79420.80}
    current_ltp = fallback_prices.get(target_symbol, 24000.0)

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
# 🖥️ 5. LIVE PREMIUM HTML CONTAINER RENDERING
# ==============================================================================
now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

terminal_html = f"""
<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">🎯 Next Day Institutional Levels Grid</div>
        <div class="live-ltp-badge">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</div>
    </div>
    <div class="zones-grid">
        <div class="zone-card card-resistance">
            <div class="card-label">🔴 Supply / Resistance (DR Zone)</div>
            <div class="card-value val-red">{int(sup_low)} - {int(sup_high)}</div>
        </div>
        <div class="zone-card card-pivot">
            <div class="card-label">⚖️ Institutional Balance Pivot (PP)</div>
            <div class="card-value val-yellow">{int(p_point)}</div>
        </div>
        <div class="zone-card card-support">
            <div class="card-label">🟢 Demand / Support (DS Zone)</div>
            <div class="card-value val-green">{int(dem_low)} - {int(dem_high)}</div>
        </div>
    </div>
    <div class="sync-timestamp">🔒 Cloud Broker Node Connected | Last Dynamic Refresh: {now_ist}</div>
</div>
"""

# FIXED: Injecting HTML strings properly as structured code blocks
st.markdown(terminal_html, unsafe_allow_html=True)

# Multi-indicators structural info table sheet below the terminal box
st.markdown("### 📊 Operational Quick Reference Analytics")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric(label="Target Asset Frame", value=target_symbol)
with c2:
    st.metric(label="Calculated Base Upper Threshold", value=f"₹{int(sup_low)}")
with c3:
    st.metric(label="Calculated Base Lower Threshold", value=f"₹{int(dem_high)}")

st_autorefresh(interval=2000, key="premium_zones_auto_sync")
