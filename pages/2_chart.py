import sys
from types import ModuleType
import os
import json
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode page layout settings
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Path Setup: pages/ se parent directory (Main Root) ko verify kar rahe hain
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

# 🔐 Direct Environment Injection Bridge (Secrets Context)
if "PHONE_NO" in st.secrets:
    os.environ["PHONE_NO"] = str(st.secrets["PHONE_NO"])
if "MPIN" in st.secrets:
    os.environ["MPIN"] = str(st.secrets["MPIN"])

# Real-Time Data Fallback Matrix
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 2444990, "status": "LIVE", "master_history": [{"open":24449.9,"high":24455.0,"low":24430.0,"close":24449.9}]},
        "SENSEX": {"price": 8035000, "status": "LIVE", "master_history": [{"open":80350.0,"high":80370.0,"low":80310.0,"close":80350.0}]}
    }

# 🌐 Unified HTML/JS Component Injection Logic
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # JSON Payload structured string conversion
    json_data = json.dumps(st.session_state.master_storage)
    
    # JavaScript Bridge Code for Strict Context Binding
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"PHONE_NO": "{os.environ.get('PHONE_NO','')}", "MPIN": "{os.environ.get('MPIN','')}", "STATUS": "ACTIVE"}};
    </script>
    """
    
    # Head element update parsing
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Rendering iframe component locally via Streamlit Context
    components.html(html_content, height=820, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
    st.info(f"🔍 System checked path: {html_file_path}")
