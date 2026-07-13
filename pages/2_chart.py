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
# 🎯 1. TERMINAL CONFIGURATION & UI HEARTBEAT TIMERS
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# Safe 5-Second layout sync block to seamlessly push stream buffers into UI
st_autorefresh(interval=5000, key="chart_rapid_websocket_sync_engine")

# 📂 Files Directory Routing System
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata

# Master Data Dictionary Memory Setup
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24150.00, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77300.00, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔐 2. UNIFIED GLOBAL CACHE SESSION BROKER (Strict Single Auth Token Lock)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_unified_nubra_session():
    """
    Official Flow: Authenticates the client exactly ONCE globally.
    Shares this unique instance across REST and WebSocket modules to prevent token drops.
    """
    try:
        client_instance = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        engine_rest = MarketData(client_instance)
        return client_instance, engine_rest
    except Exception as network_error:
        print(f"Master Session Identity Crash: {network_error}")
        return None, None

session_broker = initialize_unified_nubra_session()
shared_client, market_engine = session_broker

# ==============================================================================
# ⚡ 3. OFFICIAL V3 HISTORICAL SEED ENGINE (Pre-loads Past Candles to Grid)
# ==============================================================================
if market_engine and len(st.session_state.master_storage["NIFTY"]["master_history"]) <= 1:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=2) 
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        for asset_key in ["NIFTY", "SENSEX"]:
            ex_type = "BSE" if asset_key == "SENSEX" else "NSE"
            
            # Fetch instant baseline quote snapshot to update top display
            snap = market_engine.current_price(asset_key, exchange=ex_type)
            if snap and snap.price:
                st.session_state.master_storage[asset_key]["price"] = float(snap.price) / 100.0

            # Requesting historical contracts using standard JSON parameters
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
                        history_list = []
                        total_ticks = len(stock_chart.close)
                        
                        for i in range(total_ticks):
                            # Converting native integers (paise scale) to decimal rupees safely
                            o = float(stock_chart.open[i].value) / 100.0
                            h = float(stock_chart.high[i].value) / 100.0
                            l = float(stock_chart.low[i].value) / 100.0
                            c = float(stock_chart.close[i].value) / 100.0
                            
                            stamp = (datetime.now() - timedelta(minutes=5 * (total_ticks - i))).strftime("%Y-%m-%d %H:%M:%S")
                            
                            history_list.append({
                                "time": stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                            })
                        st.session_state.master_storage[asset_key]["master_history"] = history_list

    except Exception as history_error:
        pass

# ==============================================================================
# 🔌 4. REALTIME WEBSOCKET TICKER PIPELINE (Strict True OHLCV Stream Mod)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_live_stream_socket(_client):
    if _client is None:
        return None
    try:
        def capture_stream_ohlcv(msg):
            try:
                # ✅ Strictly extracting variables from target OHLCV wrapper payload fields
                symbol_key = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                
                if symbol_key in ["NIFTY", "SENSEX"]:
                    # Converting real time integer paise scales safely
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    
                    if c > 0:
                        target_cell = st.session_state.master_storage[symbol_key]
                        target_cell["price"] = c
                        target_cell["status"] = "LIVE"
                        
                        history = target_cell["master_history"]
                        candle_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        if len(history) > 0 and history[-1]["time"] == candle_stamp:
                            history[-1]["high"] = max(history[-1]["high"], h)
                            history[-1]["low"] = min(history[-1]["low"], l)
                            history[-1]["close"] = c
                        else:
                            history.append({
                                "time": candle_stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                            })
                            
                        if len(history) > 300:
                            history.pop(0)
            except Exception as stream_err:
                print(f"Websocket payload mapping crash: {stream_err}")

        # ✅ Re-binding to correct on_ohlcv_data callback handler
        socket_instance = websocketdata.NubraDataSocket(
            client=_client,
            on_ohlcv_data=capture_stream_ohlcv, 
            on_connect=lambda m: print("[Socket Status: CONNECTED]"),
            on_close=lambda r: print(f"Socket connection closed: {r}"),
            on_error=lambda e: print(f"Socket exception logs: {e}")
        )
        
        socket_instance.connect()
        # ✅ Using correct ohlcv subscription matching verified log schema
        socket_instance.subscribe(["NIFTY"], data_type="ohlcv", interval="5m", exchange="NSE")
        socket_instance.subscribe(["SENSEX"], data_type="ohlcv", interval="5m", exchange="BSE")
        
        return socket_instance
    except Exception as socket_error:
        print(f"WebSocket execution thread failure: {socket_error}")
        return None

active_live_socket = initialize_live_stream_socket(shared_client)

# ==============================================================================
# 🌐 5. ZERO-FLICKER HTML CANVAS DATA INJECTION BRIDGE
# ==============================================================================
for key in ["NIFTY", "SENSEX"]:
    cell = st.session_state.master_storage[key]
    if len(cell["master_history"]) == 0:
        base_val = cell["price"]
        cell["master_history"] = [
            {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "open": base_val, "high": base_val, "low": base_val, "close": base_val, "volume": 0.0}
        ]

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as file_reader:
        html_blueprint = file_reader.read()

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
    st.error("❌ System core exception: 'index.html' target module was not found.")
