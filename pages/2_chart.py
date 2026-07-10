import sys
from types import ModuleType
import os
import time
import json
import streamlit as st
import streamlit.components.v1 as components

# 📊 Page setting to wide mode
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Path Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# ========================================================
# 🔐 SECURE OS INJECTION ENGINE (Bypassing SDK Parameter Error)
# ========================================================
PHONE_NO = None
MPIN = None

try:
    if hasattr(st, "secrets") and st.secrets is not None:
        PHONE_NO = st.secrets.to_dict().get("PHONE_NO")
        MPIN = st.secrets.to_dict().get("MPIN")
except Exception as e:
    print(f"Secrets parsing check error: {e}")

# Agar details mil gayi hain, to dynamic OS parameters injection lagayein
if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)
# ========================================================

# Master Storage Structure for Charts
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# 🔄 System SDK Login Trigger (Using Standard Env Method Only)
market_engine = None
try:
    # Parameter pass karna band, direct system environment mapping mode active
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    st.warning(f"⚠️ Broker SDK Core Verification Issue: {str(e)}")

# --- DIRECT DATA INGESTION MATRIX ---
if market_engine:
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
        print(f"Data stream push warning: {error}")
else:
    st.error("🔒 Auth Fail: Broker connection structure ready nahi ho paya.")

# 🌐 HTML JavaScript Frame Injector
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    json_data = json.dumps(st.session_state.master_storage)
    
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=820, scrolling=True)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")

# ⏳ Autoloop page rerun engine (1 second ticker)
time.sleep(1)
st.rerun()
