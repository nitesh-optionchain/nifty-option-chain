import sys
from types import ModuleType
import os
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

# 🌐 Unified HTML Load Logic (LOAD ONLY ONCE)
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # JavaScript Bridge context injection (Bina dynamic arrays ke, sirf tokens)
    injection_script = f"""
    <script>
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # 🎯 RENDER FRAME JUST ONCE - NO LOOP, NO RERUN, NO FLICKER
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
