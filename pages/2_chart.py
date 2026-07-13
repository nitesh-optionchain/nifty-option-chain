import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 🎯 1. PREMIUM TERMINAL CONFIGURATION & HEARTBEAT
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🔄 5-Second Rapid UI Sync Counter to push raw memory buffer changes smoothly
st_autorefresh(interval=5000, key="chart_rapid_websocket_sync_engine")

# 📂 Paths Framework Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

# Master Data Storage Context Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24130.55, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77335.16, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔐 2. GLOBAL CACHED WEBSOCKET CONTROLLER (Zero-Collision Client Bridge)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_live_stream_socket():
    """
    Spawns a single stable, non-blocking background connection pipe.
    Listens directly to the wrapper data stream and loads it into global cache.
    """
    try:
        nubra_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        # Explicit callback loop listener functions binding
        def capture_stream_ohlcv(msg):
            try:
                # Scanning attributes matching the specific terminal log wrapper
                idx_name = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                if idx_name in ["NIFTY", "SENSEX"]:
                    # Unpacking numeric units precisely from integer scaled logs
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    v = float(getattr(msg, 'tick_volume', 0)) or float(getattr(msg, 'bucket_volume', 0))
                    
                    # Prevent zero division bugs if empty tick packages land
                    if c > 0:
                        storage = st.session_state.master_storage[idx_name]
                        storage["price"] = c
                        storage["status"] = "LIVE"
                        
                        history_arr = storage["master_history"]
                        
                        # Custom timestamp allocation logic
                        candle_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Verification mapping layer to check for dynamic updates
                        if len(history_arr) > 0 and history_arr[-1]["time"] == candle_stamp:
                            # Update existing forming candlestick parameters
                            history_arr[-1]["high"] = max(history_arr[-1]["high"], h)
                            history_arr[-1]["low"] = min(history_arr[-1]["low"], l)
                            history_arr[-1]["close"] = c
                            history_arr[-1]["volume"] += v
                        else:
                            # Push a completely new structural OHLCV candle object block
                            history_arr.append({
                                "time": candle_stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": v
                            })
                            
                        # Keep storage optimization trace arrays bounds locked
                        if len(history_arr) > 200:
                            history_arr.pop(0)
            except Exception as loop_err:
                print(f"Internal wrapper streaming error: {loop_err}")

        def capture_stream_status(msg):
            pass

        # Socket setup sequence execution
        socket_instance = websocketdata.NubraDataSocket(
            client=nubra_client,
            on_ohlcv_data=capture_stream_ohlcv,
            on_connect=capture_stream_status,
            on_close=lambda r: print(f"Connection closed: {r}"),
            on_error=lambda e: print(f"Socket tracking exception: {e}")
        )
        
        socket_instance.connect()
        # Direct subscription mapping using your verified parameter specifications
        socket_instance.subscribe(["NIFTY"], data_type="ohlcv", interval="10m", exchange="NSE")
        socket_instance.subscribe(["SENSEX"], data_type="ohlcv", interval="10m", exchange="BSE")
        
        return socket_instance
    except Exception as connection_failure:
        print(f"WebSocket execution handshake error: {connection_failure}")
        return None

# Instantiating the unified non-blocking stream receiver channel
active_live_socket = initialize_live_stream_socket()

# ==============================================================================
# 🧠 3. EMERGENCY PLACEHOLDER SEED ENGINE (Anti-Blank Grid Framework)
# ==============================================================================
# If stream arrays are completely blank initially, generates baseline candles dynamically
for asset_key in ["NIFTY", "SENSEX"]:
    if len(st.session_state.master_storage[asset_key]["master_history"]) == 0:
        base_ltp = st.session_state.master_storage[asset_key]["price"]
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Injecting structural baseline candles array list
        st.session_state.master_storage[asset_key]["master_history"] = [
            {"time": current_time_str, "open": base_ltp, "high": base_ltp * 1.002, "low": base_ltp * 0.998, "close": base_ltp, "volume": 100.0}
        ]

# ==============================================================================
# 🌐 4. ZERO-FLICKER HTML CANVAS DISPLAY MOD (High-Speed Injection System)
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Packing current thread records safely into cross-domain objects
    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Renders the interactive terminal block window directly
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ System core exception: 'index.html' canvas module could not be traced inside root folders.")
