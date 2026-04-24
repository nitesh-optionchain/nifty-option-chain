import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# 1. PAGE CONFIG
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="data_refresh")
SIG_FILE = "admin_levels_v2.json"

# 2. DIRECT DATA FETCH FUNCTION
def get_market_data(index_name):
    # Bhai, ye URL wahi hai jo aapka purana SDK use karta tha
    url = f"https://api.nubra.in/v1/market/index/{index_name}"
    headers = {"api-key": "9304768496"} # Aapki Mobile ID
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Asli API keys 'lp' aur 'ch' ho sakti hain
            return {"lp": data.get("lp", 0), "chg": data.get("ch", 0)}
        else:
            return {"lp": "Check API", "chg": 0}
    except:
        return {"lp": "Offline", "chg": 0}

# 3. ADMIN DATA LOAD
if os.path.exists(SIG_FILE):
    with open(SIG_FILE, "r") as f: sig = json.load(f)
else:
    sig = {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= UI DASHBOARD =================
st.title("🚀 SMART WEALTH AI - DIRECT LIVE")

idx_choice = st.sidebar.selectbox("Select Market", ["NIFTY", "BANKNIFTY", "SENSEX"])
live = get_market_data(idx_choice)

# Live Header
color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left:10px solid {color};">
        <h1 style="margin:0; color:white;">{idx_choice}: ₹{live['lp']}</h1>
        <p style="margin:0; color:{color}; font-size:20px;">{live['chg']}% | Live Data</p>
    </div>
""", unsafe_allow_html=True)

# Admin Panel
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("Update Dashboard"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1,"buy":v2,"tgt":v3,"sl":v4}, f)
        st.rerun()

# Signal Metrics
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])
