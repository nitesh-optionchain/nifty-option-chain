import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh

# SDK import ko handle karne ke liye logic
try:
    from nubra_sdk import NubraClient
    SDK_INSTALLED = True
except ImportError:
    SDK_INSTALLED = False

# CONFIG
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=2000, key="auto_refresh")
SIG_FILE = "admin_levels_v2.json"

# 1. SDK CONNECTION
@st.cache_resource
def get_nubra():
    if SDK_INSTALLED:
        return NubraClient(api_key="9304768496")
    return None

client = get_nubra()

# 2. DATA FETCHING
nifty = {"lp": 0, "chg": 0}
if client:
    try:
        nifty = client.get_index("NIFTY")
    except:
        pass

# 3. ADMIN DATA LOAD
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= UI DASHBOARD =================
st.title("🚀 SMART WEALTH AI - LIVE")

if not SDK_INSTALLED:
    st.error("⚠️ SDK Not Found: Please check requirements.txt for 'nubra-python-sdk'")
    st.stop() # App yahi ruk jayega agar SDK nahi mila

# Market Display
st.metric("NIFTY 50", f"₹{nifty.get('lp', 0)}", f"{nifty.get('chg', 0)}%")

# Admin Controls
with st.expander("🛠️ Admin Control Panel"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("Update Dashboard"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1, "buy":v2, "tgt":v3, "sl":v4}, f)
        st.rerun()

# Signal Display
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])
