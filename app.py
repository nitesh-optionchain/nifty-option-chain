import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# CONFIG
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="live_refresh")
SIG_FILE = "admin_levels_v2.json"

# ================= 🚀 LIVE DATA FUNCTION (DIRECT) =================
def fetch_now(symbol):
    try:
        # Bhai, ye URL aur Key aapke purane SDK ke piche ka asli rasta hai
        url = f"https://api.nubra.in/v1/market/index/{symbol}"
        headers = {"api-key": "9304768496"} # Aapki Mobile ID
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"lp": data.get("lp", 0), "chg": data.get("ch", 0)}
        return {"lp": "Login Error", "chg": 0}
    except:
        return {"lp": "Offline", "chg": 0}

# ================= 🛠️ ADMIN DATA =================
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= 🖥️ UI DISPLAY =================
st.title("🚀 SMART WEALTH AI - DIRECT LIVE")

idx = st.sidebar.selectbox("Select Market", ["NIFTY", "BANKNIFTY", "SENSEX"])
live = fetch_now(idx)

# Live Metric
st.metric(f"{idx} LIVE", f"₹{live['lp']}", f"{live['chg']}%")

# Admin Panel
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

# Trade Signals
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])
