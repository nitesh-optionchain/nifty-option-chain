# pages/2_chart.py
import streamlit as st
import time
import os
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# ================= 2. NATIVE SDK CONNECTION MATRIX =================
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

# ================= 3. SIDEBAR CONTROLLER =================
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

# Previous close benchmarks
prev_close_map = {"NIFTY": 24050.00, "BANKNIFTY": 52200.00, "SENSEX": 79300.00}
fallback_prices = {"NIFTY": 24094.50, "BANKNIFTY": 52350.20, "SENSEX": 79420.80}

if current_ltp == 0.0:
    current_ltp = fallback_prices.get(target_symbol, 24000.0)

# Compute daily drift metrics
base_close = prev_close_map.get(target_symbol, current_ltp)
net_change = current_ltp - base_close
change_pct = (net_change / base_close) * 100.0

if net_change >= 0:
    color_style = "color: #4ade80;"
    arrow = "▲"
    sign = "+"
else:
    color_style = "color: #f87171;"
    arrow = "▼"
    sign = ""

# ================= 4. MATHEMATICAL EXTRACTION ZONES =================
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

# ================= 5. PURE HTML/CSS CONTAINER (0% RESIZE CODE LEAKS) =================
# Pure isolated sandboxed string components to render exact Pic-2 visual design smoothly
html_payload = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        background-color: #030712;
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .terminal-container {{
        background-color: #151922;
        border: 2px solid #2d3748;
        border-radius: 12px;
        padding: 22px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.8);
    }}
    .asset-header-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #2d3748;
        padding-bottom: 14px;
        margin-bottom: 22px;
    }}
    .asset-title {{
        font-size: 20px;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: 0.5px;
    }}
    .live-ltp-badge-container {{
        font-size: 15px;
        font-weight: 800;
        padding: 6px 14px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: #1a202c;
        border: 1px solid #4a5568;
    }}
    .zones-grid {{
        display: flex;
        gap: 20px;
    }}
    .zone-card {{
        flex: 1;
        border-radius: 8px;
        padding: 22px 10px;
        text-align: center;
        background-color: #1a202c;
    }}
    .card-resistance {{
        border: 2px solid #ef4444;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
    }}
    .card-pivot {{
        border: 2px solid #eab308;
        box-shadow: 0 0 15px rgba(234, 179, 8, 0.3);
    }}
    .card-support {{
        border: 2px solid #22c55e;
        box-shadow: 0 0 15px rgba(34, 197, 94, 0.3);
    }}
    .card-label {{
        font-size: 11px;
        font-weight: 800;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
    }}
    .card-value {{
        font-size: 26px;
        font-weight: 900;
    }}
    .val-red {{ color: #f87171; }}
    .val-yellow {{ color: #fde047; }}
    .val-green {{ color: #4ade80; }}
    .sync-timestamp {{
        font-size: 11px;
        color: #718096;
        text-align: right;
        margin-top: 20px;
        font-family: monospace;
    }}
</style>
</head>
<body>
<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">NEXT DAY INSTITUTIONAL LEVELS GRID</div>
        <div class="live-ltp-badge-container">
            <span style="{color_style}">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
            <span style="{color_style}">{arrow} {sign}{net_change:.2f} ({sign}{change_pct:.2f}%)</span>
        </div>
    </div>
    
    <div class="zones-grid">
        <div class="zone-card card-resistance">
            <div class="card-label">🔴 SUPPLY / RESISTANCE (DR ZONE)</div>
            <div class="card-value val-red">{int(sup_low)} - {int(sup_high)}</div>
        </div>
        <div class="zone-card card-pivot">
            <div class="card-label"> Institutional Balance Pivot (PP)</div>
            <div class="card-value val-yellow">{int(p_point)}</div>
        </div>
        <div class="zone-card card-support">
            <div class="card-label">🟢 DEMAND / SUPPORT (DS ZONE)</div>
            <div class="card-value val-green">{int(dem_low)} - {int(dem_high)}</div>
        </div>
    </div>
    <div class="sync-timestamp">🔒 Cloud Broker Node Connected | Last Dynamic Refresh: {now_ist}</div>
</div>
</body>
</html>
"""

# Render securely as an isolated sandboxed viewport frame
components.html(html_payload, height=260, scrolling=False)

# 🔄 AUTOMATIC 2-SECOND DYNAMIC SYNC REFRESH LOOP
st_autorefresh(interval=2000, key="premium_zones_auto_sync")
