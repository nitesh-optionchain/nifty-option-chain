import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# Clean dynamic page configuration without any visible headers
st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

@st.cache_resource(show_spinner=False)
def get_sdk_connector():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception:
        return None

market_engine = get_sdk_connector()

if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "master_history": []},
        "SENSEX": {"price": 0, "master_history": []}
    }

# Dynamic target configuration selector block inside Sidebar
target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# Pull Historical grid sequence from SDK
if market_engine:
    try:
        symbol_name = "Nifty 50" if target_index == "NIFTY" else "SENSEX"
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        
        if not st.session_state.master_storage[target_index]["master_history"]:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=3)
            
            hist_response = market_engine.historical_data({
                "exchange": exch_name, "type": "INDEX", "values": [symbol_name],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "interval": "5m", "intraDay": True, "realTime": False
            })
            
            if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
                for candle in hist_response.candles:
                    raw_ts = getattr(candle, 'timestamp', '')
                    st.session_state.master_storage[target_index]["master_history"].append({
                        "time": raw_ts,
                        "open": float(getattr(candle, 'open', 0)) / 100,
                        "high": float(getattr(candle, 'high', 0)) / 100,
                        "low": float(getattr(candle, 'low', 0)) / 100,
                        "close": float(getattr(candle, 'close', 0)) / 100
                    })

        snap = market_engine.current_price(target_index, exchange=exch_name)
        if snap and getattr(snap, 'price', None):
            live_val = float(snap.price) / 100
            st.session_state.master_storage[target_index]["price"] = int(snap.price)
            if st.session_state.master_storage[target_index]["master_history"]:
                st.session_state.master_storage[target_index]["master_history"][-1]["close"] = live_val

    except Exception as e:
        st.sidebar.error(f"SDK Alert: {e}")

# If SDK fails, generate placeholder bars to prevent layout freeze
if not st.session_state.master_storage[target_index]["master_history"]:
    base_val = 24000.0 if target_index == "NIFTY" else 79000.0
    now_dt = datetime.now()
    for step in range(80, 0, -1):
        ts_str = (now_dt - timedelta(minutes=5 * step)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        st.session_state.master_storage[target_index]["master_history"].append({
            "time": ts_str, 
            "open": base_val + (step % 4), 
            "high": base_val + (step % 4) + 12, 
            "low": base_val + (step % 4) - 8, 
            "close": base_val + (step % 4) + 4
        })

# Bridge Data Delivery Execution
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)
    
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Render component directly matching absolute frame viewport
    components.html(html_content, height=760, scrolling=False)
    
    time.sleep(2)
    st.rerun()
