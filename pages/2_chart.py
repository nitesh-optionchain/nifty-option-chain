import sys
from types import ModuleType
import os
import json
import streamlit as st
import streamlit.components.v1 as components

# 📊 Page configuration to wide mode
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Path Setup: Kyunki ye file pages/ folder me hai,
# isliye iska parent directory hi main root folder hoga jahan index.html rakhi hai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

# 🔐 Direct Environment Injection Bridge
# Main page se login hone ke baad credentials ko hardware memory me le rahe hain
if "PHONE_NO" in st.secrets:
    os.environ["PHONE_NO"] = str(st.secrets["PHONE_NO"])
if "MPIN" in st.secrets:
    os.environ["MPIN"] = str(st.secrets["MPIN"])

# 🌐 HTML File Render Logic (Direct Internal Read from Main Root)
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Payload prepared for Javascript native WebSocket context
    auth_payload = {
        "PHONE_NO": os.environ.get("PHONE_NO", ""),
        "MPIN": os.environ.get("MPIN", ""),
        "STATUS": "ACTIVE"
    }
    
    json_data = json.dumps(auth_payload)
    html_content = html_content.replace(
        "<head>", 
        f"<head><script>window.streamAuthContext = {json_data};</script>"
    )
    
    # Rendering embedded component block
    components.html(html_content, height=780, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
    st.info(f"🔍 System checked path: {html_file_path}")
