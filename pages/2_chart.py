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
# 🎯 1. ZERO-BLINK PRECISE PAGE CONFIGURATION & REFRESH TIMERS
# ==============================================================================
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🔄 10-Second Quick UI Heartbeat Sync to push data array smoothly into javascript
st_autorefresh(interval=10000, key="chart_synchronized_heartbeat_engine")

# 📂 Paths Framework Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata

# 🔐 Secure Environment Keys Bridge
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Master Data Storage Context Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24154.00, "status": "LIVE", "master_history": []},
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
# ⚡ 3. HYBRID HISTORICAL LOADER ENGINE (Pre-loads stable database blocks)
# ==============================================================================
if market_engine and len(st.session_state.master_storage["NIFTY"]["master_history"]) == 0:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=3) 
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        def unpack_nubra_points(points_list):
            if not points_list:
                return []
            return [float(p.value) for p in points_list]

        for asset_key in ["NIFTY", "SENSEX"]:
            ex_type = "BSE" if asset_key == "SENSEX" else "NSE"
            snap = market_engine.current_price(asset_key, exchange=ex_type)
            if snap and snap.price:
                st.session_state.master_storage[asset_key]["price"] = float(snap.price) / 100.0
            
            res = market_engine.historical_data({
                "exchange": ex_type, "type": "INDEX", "values": [asset_key],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_str, "endDate": end_str, "interval": "10m",
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
                                stamp = (datetime.now() - timedelta(minutes=10 * (len(opens) - i))).strftime("%Y-%m-%d %H:%M:%S")
                                history_list.append({
                                    "time": stamp,
                                    "open": float(opens[i]/100.0), "high": float(highs[i]/100.0),
                                    "low": float(lows[i]/100.0), "close": float(closes[i]/100.0),
                                    "volume": 100.0
                                })
                            st.session_state.master_storage[asset_key]["master_history"] = history_list
                            
            if len(st.session_state.master_storage[asset_key]["master_history"]) == 0:
                base_p = st.session_state.master_storage[asset_key]["price"]
                st.session_state.master_storage[asset_key]["master_history"] = [
                    {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "open": base_p, "high": base_p, "low": base_p, "close": base_p, "volume": 1.0}
                ]
    except Exception as e:
        print(f"Historical pre-load pipeline exception: {e}")

# ==============================================================================
# 🔌 4. REALTIME LIVE BACKGROUND WEBSOCKET PIPELINE (Strict on_index_data Mod)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_live_stream_socket():
    try:
        nubra_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        # ✅ Fixed to catch index messages matching your accurate verified SDK logs
        def capture_stream_index(msg):
            try:
                idx_name = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                if idx_name in ["NIFTY", "SENSEX"]:
                    # Extraction mapping logic using strict type check conversions
                    o = float(getattr(msg, 'open', 0))
                    h = float(getattr(msg, 'high', 0))
                    l = float(getattr(msg, 'low', 0))
                    c = float(getattr(msg, 'close', 0))
                    
                    if c > 0:
                        storage = st.session_state.master_storage[idx_name]
                        storage["price"] = c
                        storage["status"] = "LIVE"
                        
                        history_arr = storage["master_history"]
                        candle_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        if len(history_arr) > 0:
                            # Dynamic real-time expansion adjustments to the forming candlestick parameters
                            history_arr[-1]["high"] = max(history_arr[-1]["high"], h)
                            history_arr[-1]["low"] = min(history_arr[-1]["low"], l)
                            history_arr[-1]["close"] = c
                        else:
                            history_arr.append({
                                "time": candle_stamp,
                                "open": o, "high": h, "low": l, "close": c, "volume": 100.0
                            })
                            
                        if len(history_arr) > 300:
                            history_arr.pop(0)
            except Exception as stream_err:
                print(f"Streaming thread mapping exception: {stream_err}")

        socket_instance = websocketdata.NubraDataSocket(
            client=nubra_client,
            on_index_data=capture_stream_index,  # ✅ Hooked strictly to index receiver function
            on_connect=lambda m: print("[Socket Connected Successfully]"),
            on_close=lambda r: print(f"Connection closed: {r}"),
            on_error=lambda e: print(f"Socket tracking exception: {e}")
        )
        
        socket_instance.connect()
        socket_instance.subscribe(["NIFTY"], data_type="index", exchange="NSE")
        socket_instance.subscribe(["SENSEX"], data_type="index", exchange="BSE")
        
        return socket_instance
    except Exception as network_error:
        print(f"WebSocket handshake crash: {network_error}")
        return None

active_live_socket = initialize_live_stream_socket()

# ==============================================================================
# 🌐 5. ZERO-FLICKER HTML CANVAS DISPLAY LAYER
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ System core folder architecture error: 'index.html' target missing.")
