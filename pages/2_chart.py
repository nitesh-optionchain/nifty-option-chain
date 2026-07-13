import sys
import os
import json
import pandas as pd
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 🎯 1. TERMINAL INTERFACE SETUP & SYSTEM COUNTER
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# Safe 5-Second layout bridge buffer to allow asynchronous data mapping
st_autorefresh(interval=5000, key="chart_rapid_websocket_sync_engine")

# 📂 Files Directory Routing System
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

# Framework Master Data States Dictionary Layout
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24185.00, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77335.00, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔌 2. NUBRA REAL WEBSOCKET ENGINE LOGIC (Directly Formulated From User Template)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_system_data_stream():
    try:
        # Initializing core cloud token handshake wrapper
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

        def on_index_data(msg):
            try:
                # Catching runtime index ticks exactly as per your terminal print logs
                symbol_key = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                
                if symbol_key in ["NIFTY", "SENSEX"]:
                    o = float(getattr(msg, 'open', 0))
                    h = float(getattr(msg, 'high', 0))
                    l = float(getattr(msg, 'low', 0))
                    c = float(getattr(msg, 'close', 0))
                    
                    if c > 0:
                        # Direct global cache memory override mutation
                        target_cell = st.session_state.master_storage[symbol_key]
                        target_cell["price"] = c
                        target_cell["status"] = "LIVE"
                        
                        history = target_cell["master_history"]
                        current_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        if len(history) > 0 and history[-1]["time"] == current_stamp:
                            history[-1]["high"] = max(history[-1]["high"], h)
                            history[-1]["low"] = min(history[-1]["low"], l)
                            history[-1]["close"] = c
                        else:
                            history.append({
                                "time": current_stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                            })
                            
                        # Limiting depth limits to optimize internal canvas speed performance
                        if len(history) > 250:
                            history.pop(0)
            except Exception as loop_e:
                print(f"Index stream collection crash: {loop_e}")

        def on_connect(msg):
            print("[status]", msg)

        def on_close(reason):
            print(f"Closed: {reason}")

        def on_error(err):
            print(f"Error: {err}")

        # Hooking elements to the native client socket infrastructure blueprint
        socket = websocketdata.NubraDataSocket(
            client=nubra,
            on_index_data=on_index_data,
            on_connect=on_connect,
            on_close=on_close,
            on_error=on_error,
        )

        socket.connect()
        # Custom real template target listings registration blocks
        socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
        socket.subscribe(["SENSEX"], data_type="index", exchange="BSE")
        
        return socket
    except Exception as initialization_err:
        print(f"Master socket startup process failed: {initialization_err}")
        return None

# Triggering persistent backend continuous client link channel
stream_broker = initialize_system_data_stream()

# ==============================================================================
# 🧠 3. STABLE SEED ARRANGEMENT PIPELINE (Ensures JavaScript Array Keys Never Stand Empty)
# ==============================================================================
for key in ["NIFTY", "SENSEX"]:
    cell = st.session_state.master_storage[key]
    if len(cell["master_history"]) == 0:
        base_val = cell["price"]
        stamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Pre-loads exact structural objects payload map matching layout inputs
        cell["master_history"] = [
            {"time": stamp_str, "open": base_val, "high": base_val, "low": base_val, "close": base_val, "volume": 0.0}
        ]

# ==============================================================================
# 🌐 4. PURE ZERO-FLICKER HTML COMPONENT INJECTION WINDOW
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
    
    # Renders the precise high-speed canvas wrapper module frame
    components.html(html_blueprint, height=850, scrolling=True)
else:
    st.error("❌ System core configuration error: 'index.html' path asset element is missing.")
