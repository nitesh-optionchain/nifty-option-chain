import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# ==============================================================================
# 🎯 1. PURE CLEAN TERMINAL INTERFACE SETUP
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Historical Data Candlestick Chart Terminal")
st.markdown("---")

# 📂 Paths Framework Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# Master Data Storage Layout
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24150.00, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77300.00, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔐 2. CACHED HANDSHAKE RESOURCE ENGINE (Single Authorization Session Lock)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_cached_nubra_engine():
    """
    Official Handshake Lock: Creates a single authenticated connection session
    globally across the app to prevent 'Unauthorized' token collisions.
    """
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as network_error:
        print(f"Master Connection Broker Exception: {network_error}")
        return None

market_engine = initialize_cached_nubra_engine()

# Asset Selector Widget
target_symbol = st.sidebar.selectbox("🔤 Select Asset", ["NIFTY", "SENSEX"], index=0)

# ==============================================================================
# ⚡ 3. STRICT DOCUMENTED HISTORICAL LOADER PIPELINE
# ==============================================================================
if market_engine:
    try:
        # Fetching last 2 days of data for stable 5m interval depths
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=2) 
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        ex_type = "BSE" if target_symbol == "SENSEX" else "NSE"
        
        # High speed snapshot price fetch
        snap = market_engine.current_price(target_symbol, exchange=ex_type)
        if snap and snap.price:
            st.session_state.master_storage[target_symbol]["price"] = float(snap.price) / 100.0

        # Official V3 REST query history implementation
        res = market_engine.historical_data({
            "exchange": ex_type, "type": "INDEX", "values": [target_symbol],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_str, "endDate": end_str, "interval": "5m",
            "intraDay": True, "realTime": False
        })
        
        if res and hasattr(res, 'result') and res.result and len(res.result) > 0:
            for inst_dict in res.result[0].values:
                stock_chart = inst_dict.get(target_symbol) if isinstance(inst_dict, dict) else getattr(inst_dict, target_symbol, None)
                
                if stock_chart and hasattr(stock_chart, 'close') and stock_chart.close:
                    history_list = []
                    total_ticks = len(stock_chart.close)
                    
                    for i in range(total_ticks):
                        # Extracting objects matching precise TimeSeriesPoint structure
                        o = float(stock_chart.open[i].value) / 100.0
                        h = float(stock_chart.high[i].value) / 100.0
                        l = float(stock_chart.low[i].value) / 100.0
                        c = float(stock_chart.close[i].value) / 100.0
                        
                        # Timestamp alignment mapping formatted for JavaScript template
                        base_time = datetime.now() - timedelta(minutes=5 * (total_ticks - i))
                        stamp = base_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        history_list.append({
                            "time": stamp,
                            "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                        })
                    st.session_state.master_storage[target_symbol]["master_history"] = history_list

    except Exception as history_error:
        st.warning(f"⚠️ Pipeline Exception Logged: {history_error}")

# Fallback initializer to ensure index.html properties never receive an empty data block
cell = st.session_state.master_storage[target_symbol]
if len(cell["master_history"]) == 0:
    base_val = cell["price"]
    cell["master_history"] = [
        {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "open": base_val, "high": base_val, "low": base_val, "close": base_val, "volume": 0.0}
    ]

# ==============================================================================
# 🌐 4. PURE ZERO-FLICKER HTML CANVAS DATA INJECTION BRIDGE
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as file_reader:
        html_blueprint = file_reader.read()

    # Dynamic JSON serialization mapping structure binding safely
    master_json = json.dumps(st.session_state.master_storage)

    javascript_context_bridge = f"""
    <script>
        window.chartData = {master_json};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_blueprint = html_blueprint.replace("<head>", f"<head>{javascript_context_bridge}")
    components.html(html_blueprint, height=850, scrolling=True)
else:
    st.error("❌ System core exception: 'index.html' module target was not found.")

# Manual Trigger Button for user-driven data retrieval
if st.button("🔄 Reload Historical Data"):
    st.cache_resource.clear()
    st.rerun()
