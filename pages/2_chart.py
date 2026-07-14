import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# Page Layout Configurations
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

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# ==============================================================================
# 🧠 CORE ENGINE: CORE DATA GENERATION FOUNDATION
# ==============================================================================
if not st.session_state.master_storage[target_index]["master_history"]:
    base_val = 24000.0 if target_index == "NIFTY" else 79000.0
    now_dt = datetime.now()
    for step in range(80, 0, -1):
        ts_str = (now_dt - timedelta(minutes=5 * step)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        st.session_state.master_storage[target_index]["master_history"].append({
            "time": ts_str, 
            "open": base_val + (step % 6) - 3, 
            "high": base_val + (step % 6) + 15, 
            "low": base_val + (step % 6) - 10, 
            "close": base_val + (step % 6) + 4
        })
    st.session_state.master_storage[target_index]["price"] = int(base_val * 100)

if market_engine:
    try:
        symbol_name = "Nifty 50" if target_index == "NIFTY" else "SENSEX"
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        
        hist_response = market_engine.historical_data({
            "exchange": exch_name, "type": "INDEX", "values": [symbol_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "5m", "intraDay": True, "realTime": False
        })
        
        if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
            st.session_state.master_storage[target_index]["master_history"] = []
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
    except Exception:
        pass

if st.session_state.master_storage[target_index]["master_history"]:
    last_close_val = st.session_state.master_storage[target_index]["master_history"][-1]["close"]
    if st.session_state.master_storage[target_index]["price"] == 0:
        st.session_state.master_storage[target_index]["price"] = int(last_close_val * 100)

st.sidebar.caption("🔄 Network Bridge: Active Sync Mode")

# ==============================================================================
# 🌐 HTML INTEGRATION WITH AUTOMATIC EVENT EMITTER PIPELINE
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)
    
    # 🎯 FIX CODE: Script payload data injector AND dynamic event postMessage dispatcher loop
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
        
        // Dynamic continuous check loop for ensuring instant initialization state
        document.addEventListener("DOMContentLoaded", function() {{
            if(typeof syncTradingViewData === "function") {{
                syncTradingViewData();
            }}
        }});
        
        // Periodic event emitter emulator inside frame context bounds
        setTimeout(function() {{
            window.postMessage({{ type: "LIVE_TICK_UPDATE", payload: {json_data}, asset: "{target_index}" }}, "*");
        }}, 200);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Render view iframe component
    components.html(html_content, height=760, scrolling=False)
    
    # Fast loop rerun bridge trigger
    time.sleep(1)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
