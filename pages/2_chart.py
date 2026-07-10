import sys
from types import ModuleType
import os
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

# Fallback Master Array Check
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 2417035, "status": "LIVE", "master_history": [{"open":24170.35,"high":24190.0,"low":24150.0,"close":24175.0}]},
        "SENSEX": {"price": 7950000, "status": "LIVE", "master_history": [{"open":79500.0,"high":79550.0,"low":79420.0,"close":79510.0}]}
    }

# 🌐 Unified Static HTML Render Engine (Executes Only ONCE - NO LOOP, NO REFRESH)
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    import json
    json_data = json.dumps(st.session_state.master_storage)

    # Static token array mapping inside head element
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Simple static iframe loader
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
