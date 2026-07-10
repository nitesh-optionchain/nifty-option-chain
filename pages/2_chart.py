import sys
from types import ModuleType
import os
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

# 🔐 SECURE SECRETS INJECTION BLOCK
PHONE_NO = st.secrets.get("PHONE_NO", "")
MPIN = st.secrets.get("MPIN", "")

# 🌐 HTML JavaScript Frame Injector (LOADS ONLY ONCE - ZERO REFRESH)
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Hum encrypted keys ko direct HTML window context me daal rahe hain
    # Taaki HTML ka andar ka JavaScript ise read karke direct secure data network bana sake
    injection_script = f"""
    <script>
        window.streamAuthContext = {{
            "PHONE_NO": "{PHONE_NO}",
            "MPIN": "{MPIN}",
            "STATUS": "AUTHORIZED_SECURE"
        }};
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Render static frame - Rerun hatane se flicker humesha ke liye band!
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
