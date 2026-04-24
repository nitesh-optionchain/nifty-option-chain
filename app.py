import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG ---
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="live_update") # Har 3 sec mein auto-fetch

SIG_FILE = "admin_levels_v2.json"

# --- 2. ASLI AUTO-FETCH LOGIC ---
def get_market_live(index_name):
    # SDK ke bina direct API connection
    url = f"https://api.nubra.in/v1/market/index/{index_name}"
    headers = {"api-key": "9304768496"} # Aapki Mobile ID
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"lp": data.get("lp", 0), "chg": data.get("ch", 0), "status": "LIVE ✅"}
        return {"lp": "ERROR", "chg": 0, "status": f"Login Req ({response.status_code})"}
    except:
        return {"lp": "OFFLINE", "chg": 0, "status": "Connection Fail"}

# --- 3. ADMIN DATA ---
def load_sig():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# --- 4. DASHBOARD UI ---
st.title("📊 SMART WEALTH AI - TERMINAL")

# Market Selection
idx = st.sidebar.selectbox("Market Select", ["NIFTY", "BANKNIFTY", "SENSEX"])
live = get_market_live(idx)
sig = load_sig()

# Live Price Card
m_color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:25px; border-radius:15px; border-left:10px solid {m_color}; text-align:center;">
        <h2 style="color:white; margin:0;">{idx}</h2>
        <h1 style="color:{m_color}; margin:10px 0; font-size:55px;">₹{live['lp']}</h1>
        <p style="color:{m_color}; margin:0; font-size:22px; font-weight:bold;">{live['chg']}% | {live['status']}</p>
    </div>
""", unsafe_allow_html=True)

# Admin Controls
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🛠️ ADMIN SIGNAL CONTROL"):
    c = st.columns(4)
    v1 = c[0].text_input("Strike", sig['stk'])
    v2 = c[1].text_input("Entry", sig['buy'])
    v3 = c[2].text_input("Target", sig['tgt'])
    v4 = c[3].text_input("SL", sig['sl'])
    if st.button("UPDATE LIVE DASHBOARD", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v1, "buy":v2, "tgt":v3, "sl":v4}, f)
        st.success("Signal Updated!")
        st.rerun()

# Trade Signals
st.markdown("---")
st.subheader("🎯 Active Signal")
met = st.columns(4)
met[0].metric("INSTRUMENT", sig['stk'])
met[1].metric("ENTRY", sig['buy'])
met[2].metric("TARGET", sig['tgt'])
met[3].metric("STOPLOSS", sig['sl'])
