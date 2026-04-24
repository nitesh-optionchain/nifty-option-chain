import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# 1. Dashboard Settings
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="auto_fetch_live") # 3 sec refresh
SIG_FILE = "admin_levels_v2.json"

# 2. Asli Auto-Fetch Function (Bina SDK ke)
def get_live_data(index_name):
    # Direct API Hit - 9304 wali ID use karke
    url = f"https://api.nubra.in/v1/market/index/{index_name}"
    headers = {"api-key": "9304768496"} 
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"lp": data.get("lp", 0), "chg": data.get("ch", 0), "status": "LIVE ✅"}
        return {"lp": "Wait", "chg": 0, "status": "Connecting..."}
    except:
        return {"lp": "OFFLINE", "chg": 0, "status": "Check Internet"}

# 3. Admin Data Load/Save
def get_sig():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# 4. UI Layout
st.title("📊 SMART WEALTH AI - TERMINAL")

idx = st.sidebar.selectbox("Market", ["NIFTY", "BANKNIFTY", "SENSEX"])
live = get_live_data(idx)
sig = get_sig()

# Live Price Banner
color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:30px; border-radius:15px; border-left:10px solid {color}; text-align:center;">
        <h2 style="color:white; margin:0;">{idx}</h2>
        <h1 style="color:{color}; margin:10px 0; font-size:60px;">₹{live['lp']}</h1>
        <p style="color:{color}; margin:0; font-size:24px; font-weight:bold;">{live['chg']}% | {live['status']}</p>
    </div>
""", unsafe_allow_html=True)

# Admin Panel
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🛠️ ADMIN SIGNAL CONTROL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("UPDATE DASHBOARD", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1, "buy":v2, "tgt":v3, "sl":v4}, f)
        st.success("Updated!")
        st.rerun()

# Trade Signal Display
st.markdown("---")
st.subheader("🎯 Active Signal")
m = st.columns(4)
m[0].metric("INSTRUMENT", sig['stk'])
m[1].metric("ENTRY PRICE", sig['buy'])
m[2].metric("TARGET", sig['tgt'])
m[3].metric("STOPLOSS", sig['sl'])
