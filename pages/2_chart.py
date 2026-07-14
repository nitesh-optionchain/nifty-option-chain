import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode configuration
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Paths Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 🔌 BROKER INTERFACES CONNECTIONS
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 SECURE OS INJECTION ENGINE
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# 🔄 System SDK Login Trigger
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    print(f"SDK Engine Error: {str(e)}")

if not market_engine:
    st.error("🔒 Auth Fail: Broker connection structure ready nahi ho paya.")
    st.stop()

# Master Storage Structure Initialization
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🧠 CORE ENGINE: PULL 3-DAYS HISTORICAL DATA WITH STRICTOR COMPATIBILITY KEYS
# ==============================================================================
indices_to_fetch = [("NIFTY", "Nifty 50", "NSE"), ("SENSEX", "SENSEX", "BSE")]

for target_id, symbol_name, exch_name in indices_to_fetch:
    if not st.session_state.master_storage[target_id]["master_history"]:
        try:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=3)
            
            hist_response = market_engine.historical_data({
                "exchange": exch_name,
                "type": "INDEX",
                "values": [symbol_name],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "interval": "5m",
                "intraDay": True,
                "realTime": False
            })
            
            if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
                for candle in hist_response.candles:
                    raw_ts = getattr(candle, 'timestamp', '')
                    # JavaScript frameworks date/time formatting key match parameters
                    st.session_state.master_storage[target_id]["master_history"].append({
                        "time": raw_ts,
                        "date": raw_ts, # Compatibility key duplication
                        "open": float(getattr(candle, 'open', 0)) / 100,
                        "high": float(getattr(candle, 'high', 0)) / 100,
                        "low": float(getattr(candle, 'low', 0)) / 100,
                        "close": float(getattr(candle, 'close', 0)) / 100
                    })
        except Exception as e:
            print(f"Error fetching historical foundation for {target_id}: {e}")

# ==============================================================================
# ⚡ LIVE STREAM COUPLING LAYER
# ==============================================================================
try:
    # 1. Update NIFTY Live Node
    nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
    if nifty_snap and getattr(nifty_snap, 'price', None):
        real_nifty = float(nifty_snap.price) / 100
        st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
        st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
        
        if st.session_state.master_storage["NIFTY"]["master_history"]:
            st.session_state.master_storage["NIFTY"]["master_history"][-1]["close"] = real_nifty
            if real_nifty > st.session_state.master_storage["NIFTY"]["master_history"][-1]["high"]:
                st.session_state.master_storage["NIFTY"]["master_history"][-1]["high"] = real_nifty
            if real_nifty < st.session_state.master_storage["NIFTY"]["master_history"][-1]["low"]:
                st.session_state.master_storage["NIFTY"]["master_history"][-1]["low"] = real_nifty

    # 2. Update SENSEX Live Node
    sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
    if sensex_snap and getattr(sensex_snap, 'price', None):
        real_sensex = float(sensex_snap.price) / 100
        st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
        st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
        
        if st.session_state.master_storage["SENSEX"]["master_history"]:
            st.session_state.master_storage["SENSEX"]["master_history"][-1]["close"] = real_sensex
            if real_sensex > st.session_state.master_storage["SENSEX"]["master_history"][-1]["high"]:
                st.session_state.master_storage["SENSEX"]["master_history"][-1]["high"] = real_sensex
            if real_sensex < st.session_state.master_storage["SENSEX"]["master_history"][-1]["low"]:
                st.session_state.master_storage["SENSEX"]["master_history"][-1]["low"] = real_sensex
                
except Exception as data_err:
    print(f"Tick collect alert: {data_err}")

# Override context variables to force unfreeze signal in widget
for k in st.session_state.master_storage:
    st.session_state.master_storage[k]["status"] = "LIVE"

# ==============================================================================
# 🌐 HTML JAVASCRIPT BRIDGE INJECTION
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
        
        window.addEventListener("message", function(event) {{
            if (event.data && event.data.type === "LIVE_TICK_UPDATE") {{
                window.chartData = event.data.payload;
                if(typeof fetchUpdates === "function") {{
                    fetchUpdates();
                }}
            }}
        }});
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=850, scrolling=True)
    
    time.sleep(1)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
