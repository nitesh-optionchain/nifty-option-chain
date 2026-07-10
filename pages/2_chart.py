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
# 🔐 STREAMLIT CLOUD DEEP-SECRET PULL ENGINE
# ========================================================
# Agar dynamic dict access block hai, toh hum internal items parse karenge
PHONE_NO = None
MPIN = None

try:
    if hasattr(st, "secrets") and st.secrets is not None:
        # Pura dict object directly call kar rahe hain setting check karne ke liye
        PHONE_NO = st.secrets.to_dict().get("PHONE_NO")
        MPIN = st.secrets.to_dict().get("MPIN")
except Exception as e:
    print(f"Secrets parsing error: {e}")

# OS Level backup fallback injection
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

# 🔄 System SDK Login Trigger
market_engine = None
if PHONE_NO and MPIN:
    try:
        client = InitNubraSdk(NubraEnv.PROD, phone_no=str(PHONE_NO), mpin=str(MPIN))
        market_engine = MarketData(client)
    except Exception as e:
        st.warning(f"⚠️ Broker SDK Authentication issue: {str(e)}")
else:
    # Safe system login logic without UI display
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        market_engine = MarketData(client)
    except Exception as e:
        pass

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
        print(f"Data engine tick fail: {error}")
else:
    # Agar abhi bhi setting block hai, toh screen par warning alert dikhega
    st.error("🔒 Security Key Missing: Streamlit Cloud settings se secrets dictionary block aa rahi hai.")

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
