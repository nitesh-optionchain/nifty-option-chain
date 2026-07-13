import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 🎯 1. OPTIMIZED ENGINE & PAGE SETUP (Zero Blink Architecture)
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🔄 SAFE EVENT TIMER LOCK: strictly 40 seconds loop interval counter
# Pure session mapping configuration logic to prevent thread flickering
st_autorefresh(interval=40000, key="chart_synchronized_heartbeat_engine")

# 📂 Paths Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Secure Environment Keys Bridge
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# ==============================================================================
# 🔐 2. RESOURCE CACHE CONTROLLER (Strict Single Authorization Lock)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_cached_nubra_engine():
    """
    Prevents duplicate authorization calls during fast script re-runs.
    Ensures a single stable connection instance is kept alive globally.
    """
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as network_error:
        print(f"Master Connection Broker Exception: {network_error}")
        return None

# Instantiating the cached single-instance stream connector
market_engine = initialize_cached_nubra_engine()

# Master Session State Storage Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# ⚡ 3. CORE OPTIMIZED DATA INTEGRATION PIPELINE (OHLC Unified Conversion)
# ==============================================================================
if market_engine:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=4) # Clean range depth mapping for 5m intervals
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        # Dynamic array unpacking tool matching the official sdk signature rules
        def unpack_nubra_points(points_list):
            if not points_list:
                return []
            return [float(p.value) for p in points_list]

        # --- PIPELINE LAYER A: NIFTY HISTORICAL OHLC GENERATION ---
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
            st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
            
            try:
                nifty_res = market_engine.historical_data({
                    "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if nifty_res and hasattr(nifty_res, 'result') and nifty_res.result and len(nifty_res.result) > 0:
                    for instrument_dict in nifty_res.result[0].values:
                        if "NIFTY" in instrument_dict:
                            stock_chart = instrument_dict["NIFTY"]
                            opens = unpack_nubra_points(stock_chart.open)
                            highs = unpack_nubra_points(stock_chart.high)
                            lows = unpack_nubra_points(stock_chart.low)
                            closes = unpack_nubra_points(stock_chart.close)
                            
                            if len(opens) > 0:
                                st.session_state.master_storage["NIFTY"]["master_history"] = [
                                    {"open": opens[i]/100, "high": highs[i]/100, "low": lows[i]/100, "close": closes[i]/100}
                                    for i in range(len(opens))
                                ]
            except Exception:
                pass

        # --- PIPELINE LAYER B: SENSEX HISTORICAL OHLC GENERATION ---
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
            st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
            
            try:
                sensex_res = market_engine.historical_data({
                    "exchange": "BSE", "type": "INDEX", "values": ["SENSEX"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if sensex_res and hasattr(sensex_res, 'result') and sensex_res.result and len(sensex_res.result) > 0:
                    for instrument_dict in sensex_res.result[0].values:
                        if "SENSEX" in instrument_dict:
                            stock_chart_s = instrument_dict["SENSEX"]
                            opens_s = unpack_nubra_points(stock_chart_s.open)
                            highs_s = unpack_nubra_points(stock_chart_s.high)
                            lows_s = unpack_nubra_points(stock_chart_s.low)
                            closes_s = unpack_nubra_points(stock_chart_s.close)
                            
                            if len(opens_s) > 0:
                                st.session_state.master_storage["SENSEX"]["master_history"] = [
                                    {"open": opens_s[i]/100, "high": highs_s[i]/100, "low": lows_s[i]/100, "close": closes_s[i]/100}
                                    for i in range(len(opens_s))
                                ]
            except Exception:
                pass
            
    except Exception as error:
        print(f"⚠️ Live synchronization metrics downstream delay: {error}")

# ==============================================================================
# 🌐 4. SINGLE SINGLE-INSTANCE IFRAME MOUNT (Zero-Flicker Injection Layout)
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Packing current session values into standard text frames
    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # strictly mounts the chart sandbox framework down inside a stable iframe block
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ Root location directory error: 'index.html' target module was not found.")
