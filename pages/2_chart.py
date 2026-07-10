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

# App main directory path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 Direct Environment Injection Bridge
# Streamlit Cloud secrets ko direct system memory me push kar rahe hain
if "PHONE_NO" in st.secrets:
    os.environ["PHONE_NO"] = str(st.secrets["PHONE_NO"])
if "MPIN" in st.secrets:
    os.environ["MPIN"] = str(st.secrets["MPIN"])

# 🌐 HTML File Render Logic (Direct Local Context)
# Hum bina kisi third-party link ke index.html ko safe injection ke sath chalayenge
html_file_path = os.path.join(BASE_DIR, 'index.html')

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Placeholder database schema injection taaki HTML/JS load hote hi tokens read kar sake
    auth_payload = {
        "PHONE_NO": os.environ.get("PHONE_NO", ""),
        "MPIN": os.environ.get("MPIN", ""),
        "STATUS": "ACTIVE"
    }
    
    # Data stream replacement bridge inside HTML structure
    json_data = json.dumps(auth_payload)
    html_content = html_content.replace(
        "<head>", 
        f"<head><script>window.streamAuthContext = {json_data};</script>"
    )
    
    # Rendering embedded component block
    components.html(html_content, height=780, scrolling=True)
else:
    # Fallback if file structure is outside local deployment context
    st.error("❌ 'index.html' file chart repository ke main folder me nahi mili!")
    st.info("💡 Kripya ensure karein ki aapki repository ke main folder me index.html uploaded hai.")
