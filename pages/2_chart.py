import sys
from types import ModuleType
import os
import time
import json
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

# 🔐 SECURE OS INJECTION ENGINE
PHONE_NO = None
MPIN = None

try:
    if hasattr(st, "secrets") and st.secrets is not None:
        PHONE_NO = st.secrets.to_dict().get("PHONE_NO")
        MPIN = st.secrets.to_dict().get("MPIN")
except Exception as e:
    print(f"Secrets check warning: {e}")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Master Storage Framework Setup
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# 🔄 System SDK Login Trigger
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    print(f"SDK Engine Error: {str(e)}")

# ========================================================
# 🎯 100% SMOOTH FRAME RENDER CONTROLLER (NO MORE RERUN)
# ========================================================
# Ek single fixed container jisme dashboard stable rahega bina refresh huye
chart_container = st.empty()

if not market_engine:
    st.error("🔒 Auth Fail: Broker connection structure ready nahi ho paya.")
    st.stop()

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # 🔄 ETERNAL DATA INGESTION MATRIX
    # Yeh loop bina page ko hilaaye sirf iframe ke andar data dynamically pass karega
    while True:
        try:
            # 1. Fetch NIFTY
            nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
            if nifty_snap and nifty_snap.price:
                real_nifty = float(nifty_snap.price) / 100
                st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
                st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
                st.session_state.master_storage["NIFTY"]["master_history"].append({
                    "open": real_nifty, "high": real_nifty, "low": real_nifty, "close": real_nifty
                })
                if len(st.session_state.master_storage["NIFTY"]["master_history"]) > 500:
                    st.session_state.master_storage["NIFTY"]["master_history"].pop(0)

            # 2. Fetch SENSEX
            sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
            if sensex_snap and sensex_snap.price:
                real_sensex = float(sensex_snap.price) / 100
                st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
                st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
                st.session_state.master_storage["SENSEX"]["master_history"].append({
                    "open": real_sensex, "high": real_sensex, "low": real_sensex, "close": real_sensex
                })
                if len(st.session_state.master_storage["SENSEX"]["master_history"]) > 500:
                    st.session_state.master_storage["SENSEX"]["master_history"].pop(0)

        except Exception as error:
            print(f"Data stream warning: {error}")

        # JSON State generation
        json_data = json.dumps(st.session_state.master_storage)
        
        injection_script = f"""
        <script>
            window.chartData = {json_data};
            window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
        </script>
        """
        
        updated_html = html_content.replace("<head>", f"<head>{injection_script}")
        
        # Container ko dynamic text overwrite kar rahe hain bina frame tode
        with chart_container:
            components.html(updated_html, height=820, scrolling=True)
            
        # ⏳ Perfect 1 Second Delay loop without breaking frontend UI
        time.sleep(1)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
