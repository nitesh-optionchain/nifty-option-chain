import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh

# SDK Load Check
try:
    from nubra_sdk import NubraClient
    SDK_MODE = True
except ImportError:
    SDK_MODE = False

st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=2000, key="auto_fetch")
SIG_FILE = "admin_levels_v2.json"

# 1. SDK Connection
@st.cache_resource
def get_client():
    if SDK_MODE:
        return NubraClient(api_key="9304768496")
    return None

client = get_client()

# 2. Data Fetching Logic
nifty = {"lp": "Wait...", "chg": "0"}
if client:
    try:
        nifty = client.get_index("NIFTY")
    except:
        pass

# 3. Admin Data
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= UI =================
st.title("🚀 SMART WEALTH AI - AUTO FETCH")

if not SDK_MODE:
    st.error("❌ SDK Not Found! Please check requirements.txt for 'nubra-python-sdk'")
else:
    st.success("✅ Connected to Nubra SDK")

# Market Display
c1, c2 = st.columns(2)
c1.metric("NIFTY 50", nifty.get('lp'), f"{nifty.get('chg')}%")

# Admin Panel
with st.expander("🛠️ Admin Control"):
    col = st.columns(4)
    v1 = col[0].text_input("Strike", sig['stk'])
    v2 = col[1].text_input("Entry", sig['buy'])
    v3 = col[2].text_input("Target", sig['tgt'])
    v4 = col[3].text_input("SL", sig['sl'])
    if st.button("Update Dashboard"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1,"buy":v2,"tgt":v3,"sl":v4}, f)
        st.rerun()

# Signal Area
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])
