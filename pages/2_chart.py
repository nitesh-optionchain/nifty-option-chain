import sys
from types import ModuleType
import os
import time
import json
import threading
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode page configuration
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

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Direct Environment Injection Bridge
if "PHONE_NO" in st.secrets:
    os.environ["PHONE_NO"] = str(st.secrets["PHONE_NO"])
if "MPIN" in st.secrets:
    os.environ["MPIN"] = str(st.secrets["MPIN"])

PHONE_NO = os.environ.get("PHONE_NO")
MPIN = os.environ.get("MPIN")

def get_nubra_session():
    try:
        if PHONE_NO and MPIN:
            return InitNubraSdk(NubraEnv.PROD, phone_no=str(PHONE_NO), mpin=str(MPIN))
        return InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except Exception as e:
        print(f"SDK Login Exception: {str(e)}")
        return None

# Dual Asset Main Memory Matrix
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 2444990, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 8035000, "status": "LIVE", "master_history": []}
    }

# 🔄 LIVE MARKET BACKGROUND WEBSOCKET TICKER PIPELINE
if "pipeline_active" not in st.session_state:
    
    def fetch_data_stream_loop():
        print("🚀 Dual Asset Live Master Pipeline Starting...")
        thread_client = get_nubra_session()
        thread_market_engine = MarketData(thread_client) if thread_client else None
        
        if not thread_market_engine:
            print("❌ Ticker cancelled: Thread environment cannot access auth structures.")
            return

        while True:
            try:
                # 1. Fetch NIFTY Ticks
                nifty_snap = thread_market_engine.current_price("NIFTY", exchange="NSE")
                if nifty_snap and nifty_snap.price:
                    real_nifty = float(nifty_snap.price) / 100
                    st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
                    st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
                    st.session_state.master_storage["NIFTY"]["master_history"].append({
                        "open": real_nifty, "high": real_nifty, "low": real_nifty, "close": real_nifty
                    })
                    if len(st.session_state.master_storage["NIFTY"]["master_history"]) > 1000:
                        st.session_state.master_storage["NIFTY"]["master_history"].pop(0)

                # 2. Fetch SENSEX Ticks
                sensex_snap = thread_market_engine.current_price("SENSEX", exchange="BSE")
                if sensex_snap and sensex_snap.price:
                    real_sensex = float(sensex_snap.price) / 100
                    st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
                    st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
                    st.session_state.master_storage["SENSEX"]["master_history"].append({
                        "open": real_sensex, "high": real_sensex, "low": real_sensex, "close": real_sensex
                    })
                    if len(st.session_state.master_storage["SENSEX"]["master_history"]) > 1000:
                        st.session_state.master_storage["SENSEX"]["master_history"].pop(0)
                            
            except Exception as error:
                print(f"Data Pipe Warning: {error}")
            time.sleep(1)

    data_thread = threading.Thread(target=fetch_data_stream_loop, daemon=True)
    data_thread.start()
    st.session_state.pipeline_active = True

# 🌐 Unified HTML/JS Component Injection Logic
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    json_data = json.dumps(st.session_state.master_storage)
    
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"PHONE_NO": "{PHONE_NO}", "MPIN": "{MPIN}", "STATUS": "ACTIVE"}};
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=820, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
