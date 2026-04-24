import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# 1. SETUP
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="auto_refresh_data")
SIG_FILE = "admin_levels_v2.json"

# 2. AUTO-FETCH LOGIC (Direct Connection)
def fetch_market_data(index_name):
    # Bhai, hum direct URL use kar rahe hain kyunki SDK Python 3.14 pe nahi chal raha
    url = f"https://api.nubra.in/v1/market/index/{index_name}"
    headers = {"api-key": "9304768496"} # Aapki Mobile ID
    
    try:
        # Bina kisi SDK ke direct internet se data mangwana
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"lp": data.get("lp", 0), "chg": data.get("ch", 0)}
        return {"lp": "Login Error", "chg": 0}
    except:
        return {"lp": "Offline", "chg": 0}

# 3. ADMIN DATA LOAD
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= 🖥️ DASHBOARD UI =================
st.title("🚀 SMART WEALTH AI - LIVE TERMINAL")

# Market Selection
idx = st.sidebar.selectbox("Market Select", ["NIFTY", "BANKNIFTY", "SENSEX"])
live = fetch_market_data(idx)

# Live Metric Display
color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left:10px solid {color}; text-align:center;">
        <h2 style="color:white; margin:0;">{idx} LIVE PRICE</h2>
        <h1 style="color:{color}; margin:10px 0; font-size:50px;">₹{live['lp']}</h1>
        <p style="color:{color}; margin:0; font-size:20px;">{live['chg']}% Change</p>
    </div>
""", unsafe_allow_html=True)

# Admin Controls
st.markdown("---")
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("UPDATE DASHBOARD", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1, "buy":v2, "tgt":v3, "sl":v4}, f)
        st.success("Signals Updated!")
        st.rerun()

# Signal Display
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])
