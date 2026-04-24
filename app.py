import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH (Har 3 second mein auto-fetch karega)
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="auto_fetch_live")

SIG_FILE = "admin_levels.json"

# 2. DATA FETCH FUNCTION (Purana Direct Method)
def get_market_data():
    url = "https://api.nubra.in/v1/market/index/NIFTY"
    headers = {"api-key": "9304768496"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"lp": "Wait...", "ch": "0"}

# 3. ADMIN DATA LOAD
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f:
        sig = json.load(f)
else:
    sig = {"stk": "-", "buy": "-", "tgt": "-", "sl": "-"}

# ================= UI DASHBOARD =================
st.title("📊 SMART WEALTH AI - LIVE")

# Nifty Price Display
data = get_market_data()
lp = data.get('lp', 'Wait...')
ch = data.get('ch', '0')

st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:10px; border-left:8px solid #00FF00;">
        <h3 style="color:white; margin:0;">NIFTY 50</h3>
        <h1 style="color:#00FF00; margin:5px 0;">₹{lp} <span style="font-size:20px;">({ch}%)</span></h1>
    </div>
""", unsafe_allow_html=True)

# Admin Panel (For updating signals)
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    
    if st.button("UPDATE DASHBOARD", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk": v1, "buy": v2, "tgt": v3, "sl": v4}, f)
        st.success("Signals Updated!")
        st.rerun()

# Trade Signals Display
st.markdown("---")
st.subheader("🎯 ACTIVE SIGNAL")
m = st.columns(4)
m[0].metric("INSTRUMENT", sig['stk'])
m[1].metric("ENTRY", f"₹{sig['buy']}")
m[2].metric("TARGET", f"₹{sig['tgt']}")
m[3].metric("STOPLOSS", f"₹{sig['sl']}")
