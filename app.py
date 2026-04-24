import os
import sys
import json

# 1. PATH FIX (Sabse pehle ye line honi chahiye)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# 2. DEBUG MODE: Check what is missing
try:
    import aiohttp
    AIO_OK = "✅ Installed"
except ImportError:
    AIO_OK = "❌ Missing (Check requirements.txt)"

try:
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    from nubra_python_sdk.ticker import websocketdata
    SDK_OK = "✅ Found"
except ImportError as e:
    SDK_OK = f"❌ Error: {e}"

# Dashboard Title
st.set_page_config(page_title="SMART WEALTH AI - DEBUG", layout="wide")
st.title("🚀 Smart Wealth AI - Diagnostic Mode")

# --- DEBUG PANEL ---
with st.expander("🔍 System Check (Check this if App Fails)", expanded=True):
    c1, c2 = st.columns(2)
    c1.write(f"**Aiohttp Status:** {AIO_OK}")
    c2.write(f"**SDK Status:** {SDK_OK}")
    
    # Path Check
    st.write("**Current Files in Repository:**")
    st.code(os.listdir("."))

# --- AUTH & MAIN LOGIC ---
if SDK_OK == "✅ Found" and AIO_OK == "✅ Installed":
    # Yahan aapka baki ka pura Dashboard wala code aayega
    st.success("Everything is ready! Please login below.")
    
    if "is_auth" not in st.session_state: st.session_state.is_auth = False
    
    if not st.session_state.is_auth:
        u_id = st.text_input("Mobile ID", type="password")
        if st.button("Login"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
    else:
        st.write("### Welcome to Live Dashboard")
        # Dashboard code here...
else:
    st.warning("⚠️ Error Found! Please fix the 'System Check' items above.")
    st.info("💡 Hint: Agar aiohttp missing hai, toh Streamlit Cloud mein 'Reboot App' zaroor karein.")import os
import sys
import json

# 1. PATH FIX (Sabse pehle ye line honi chahiye)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# 2. DEBUG MODE: Check what is missing
try:
    import aiohttp
    AIO_OK = "✅ Installed"
except ImportError:
    AIO_OK = "❌ Missing (Check requirements.txt)"

try:
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    from nubra_python_sdk.ticker import websocketdata
    SDK_OK = "✅ Found"
except ImportError as e:
    SDK_OK = f"❌ Error: {e}"

# Dashboard Title
st.set_page_config(page_title="SMART WEALTH AI - DEBUG", layout="wide")
st.title("🚀 Smart Wealth AI - Diagnostic Mode")

# --- DEBUG PANEL ---
with st.expander("🔍 System Check (Check this if App Fails)", expanded=True):
    c1, c2 = st.columns(2)
    c1.write(f"**Aiohttp Status:** {AIO_OK}")
    c2.write(f"**SDK Status:** {SDK_OK}")
    
    # Path Check
    st.write("**Current Files in Repository:**")
    st.code(os.listdir("."))

# --- AUTH & MAIN LOGIC ---
if SDK_OK == "✅ Found" and AIO_OK == "✅ Installed":
    # Yahan aapka baki ka pura Dashboard wala code aayega
    st.success("Everything is ready! Please login below.")
    
    if "is_auth" not in st.session_state: st.session_state.is_auth = False
    
    if not st.session_state.is_auth:
        u_id = st.text_input("Mobile ID", type="password")
        if st.button("Login"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
    else:
        st.write("### Welcome to Live Dashboard")
        # Dashboard code here...
else:
    st.warning("⚠️ Error Found! Please fix the 'System Check' items above.")
    st.info("💡 Hint: Agar aiohttp missing hai, toh Streamlit Cloud mein 'Reboot App' zaroor karein.")
