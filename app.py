import streamlit as st
import pandas as pd
import requests
import json
import os

# --- Page Setup ---
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
SIG_FILE = "admin_levels.json"

# --- Purana Data Fetch Function ---
def fetch_nifty():
    url = "https://api.nubra.in/v1/market/index/NIFTY"
    headers = {"api-key": "9304768496"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {"lp": "0", "ch": "0"}

# --- Load Admin Data ---
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-", "buy":"-", "tgt":"-", "sl":"-"}

# --- UI Header ---
st.title("🚀 SMART WEALTH AI - DASHBOARD")

# Live Nifty Price
data = fetch_nifty()
col1, col2 = st.columns(2)
col1.metric("NIFTY 50", f"₹{data.get('lp')}", f"{data.get('ch')}%")

if st.button("🔄 Refresh Data"):
    st.rerun()

# --- Admin Section ---
st.markdown("---")
with st.expander("🛠️ ADMIN CONTROL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("UPDATE DASHBOARD"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1, "buy":v2, "tgt":v3, "sl":v4}, f)
        st.success("Updated Successfully!")
        st.rerun()

# --- Display Final Signals ---
st.markdown("### 🎯 ACTIVE TRADING SIGNAL")
m = st.columns(4)
m[0].metric("INSTRUMENT", sig['stk'])
m[1].metric("ENTRY", sig['buy'])
m[2].metric("TARGET", sig['tgt'])
m[3].metric("STOPLOSS", sig['sl'])
