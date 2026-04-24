import os
import sys
import json
import streamlit as st

# 1. PATH FIX
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. DEBUG CHECK
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

# Dashboard Config
st.set_page_config(page_title="SMART WEALTH AI - DIAGNOSTIC", layout="wide")
st.title("🚀 Smart Wealth AI - System Check")

# --- DEBUG PANEL ---
with st.expander("🔍 System Diagnostics", expanded=True):
    c1, c2 = st.columns(2)
    c1.write(f"**Aiohttp Status:** {AIO_OK}")
    c2.write(f"**SDK Status:** {SDK_OK}")
    
    st.write("**Current Files in Repository:**")
    try:
        st.code(os.listdir("."))
    except Exception as e:
        st.error(f"Could not list files: {e}")

st.divider()

# --- MAIN LOGIC ---
if SDK_OK == "✅ Found" and AIO_OK == "✅ Installed":
    st.success("System is Healthy! Proceeding to Login...")
    
    if "is_auth" not in st.session_state:
        st.session_state.is_auth = False
    
    if not st.session_state.is_auth:
        u_id = st.text_input("Mobile ID", type="password", key="login_id")
        if st.button("Login"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
    else:
        st.info("Aapka Dashboard ab live hone ke liye taiyaar hai.")
        # Dashboard ka baki code yahan dalenge ek baar ye screen chal jaye
else:
    st.warning("⚠️ Error Found! Please fix the System Check items above.")
    st.info("💡 Hint: Agar aiohttp missing hai, toh Streamlit Cloud mein 'Reboot App' zaroor karein.")
