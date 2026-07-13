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
# 🎯 1. TERMINAL CONFIGURATION & Rapid UI Refresh Engine
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# Safe 5-Second layout sync block to prevent engine thread flickering
st_autorefresh(interval=5000, key="chart_rapid_websocket_sync_engine")

# 📂 Files Directory Routing System
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata

# Master Data Dictionary Framework Initialization
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24185.00, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77335.00, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔐 2. GLOBAL CACHED RESOURCE ENGINE (Token Identity Broker Lock)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_cached_nubra_engine():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as network_error:
        print(f"Master Session Identity Crash: {network_error}")
        return None

market_engine = initialize_cached_nubra_engine()

# ==============================================================================
# 🔌 3. NUBRA REAL WEBSOCKET ENGINE LOGIC (Triggered on_index_data Function Mod)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_system_data_stream():
    try:
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

        def on_index_data(msg):
            try:
                symbol_key = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                
                if symbol_key in ["NIFTY", "SENSEX"]:
                    # Continuous live pricing stream variable update
                    c = float(getattr(msg, 'close', 0))
                    o = float(getattr(msg, 'open', c))
                    h = float(getattr(msg, 'high', c))
                    l = float(getattr(msg, 'low', c))
                    
                    if c > 0:
                        target_cell = st.session_state.master_storage[symbol_key]
                        target_cell["price"] = c
                        target_cell["status"] = "LIVE"
                        
                        history = target_cell["master_history"]
                        current_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Realtime index candle generation block logic
                        if len(history) > 0 and history[-1]["time"] == current_stamp:
                            history[-1]["high"] = max(history[-1]["high"], h)
                            history[-1]["low"] = min(history[-1]["low"], l)
                            history[-1]["close"] = c
                        else:
                            history.append({
                                "time": current_stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                            })
                            
                        if len(history) > 300:
                            history.pop(0)
            except Exception as loop_e:
                print(f"Index stream collection crash: {loop_e}")

        socket = websocketdata.NubraDataSocket(
            client=nubra,
            on_index_data=on_index_data,
            on_connect=lambda m: print("[Socket Status: CONNECTED]"),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}"),
        )
        socket.connect()
        socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
        socket.subscribe(["SENSEX"], data_type="index", exchange="BSE")
        return socket
    except Exception as initialization_err:
        print(f"Master socket startup process failed: {initialization_err}")
        return None

stream_broker = initialize_system_data_stream()

# ==============================================================================
# 🧠 4. PRECISE HISTORICAL PACKET FEEDER (Fills the baseline layout grid structure)
# ==============================================================================
if market_engine:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=2) 
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        def unpack_nubra_points(points_list):
            if not points_list:
                return []
            return [float(p.value) for p in points_list]

        for asset_key in ["NIFTY", "SENSEX"]:
            # Baseline checking: load history array only if currently empty
            if len(st.session_state.master_storage[asset_key]["master_history"]) <= 1:
                ex_type = "BSE" if asset_key == "SENSEX" else "NSE"
                
                res = market_engine.historical_data({
                    "exchange": ex_type, "type": "INDEX", "values": [asset_key],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                
                if res and hasattr(res, 'result') and res.result and len(res.result) > 0:
                    for inst_dict in res.result[0].values:
                        stock_chart = inst_dict.get(asset_key) if isinstance(inst_dict, dict) else getattr(inst_dict, asset_key, None)
                        if stock_chart and hasattr(stock_chart, 'close') and stock_chart.close:
                            opens = unpack_nubra_points(stock_chart.open)
                            highs = unpack_nubra_points(stock_chart.high)
                            lows = unpack_nubra_points(stock_chart.low)
                            closes = unpack_nubra_points(stock_chart.close)
                            
                            if len(opens) > 0:
                                history_list = []
                                for i in range(len(opens)):
                                    # Formats exact structural date tags to seamlessly match javascript inputs
                                    stamp = (datetime.now() - timedelta(minutes=5 * (len(opens) - i))).strftime("%Y-%m-%d %H:%M:%S")
                                    history_list.append({
                                        "time": stamp,
                                        "open": float(opens[i]/100.0), "high": float(highs[i]/100.0),
                                        "low": float(lows[i]/100.0), "close": float(closes[i]/100.0),
                                        "volume": 100.0
                                    })
                                st.session_state.master_storage[asset_key]["master_history"] = history_list
                                
            # Final safety guard fallback
            if len(st.session_state.master_storage[asset_key]["master_history"]) == 0:
                base_val = st.session_state.master_storage[asset_key]["price"]
                st.session_state.master_storage[asset_key]["master_history"] = [
                    {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "open": base_val, "high": base_val, "low": base_val, "close": base_val, "volume": 0.0}
                ]
    except Exception as h_err:
        print(f"Feeder error logs: {h_err}")

# ==============================================================================
# 🌐 5. ZERO-FLICKER HTML COMPONENT INJECTION WINDOW
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as file_reader:
        html_blueprint = file_reader.read()

    json_data = json.dumps(st.session_state.master_storage)

    javascript_context_bridge = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_blueprint = html_blueprint.replace("<head>", f"<head>{javascript_context_bridge}")
    components.html(html_blueprint, height=850, scrolling=True)
else:
    st.error("❌ System core configuration error: 'index.html' target module was not found.")
