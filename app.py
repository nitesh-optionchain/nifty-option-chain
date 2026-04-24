import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI - FIXED", layout="wide")
st_autorefresh(interval=5000, key="fixed_refresh") # 5 sec refresh
SIG_FILE = "admin_levels.json"

# ================= 🔐 SIMPLE LOGIN =================
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if not st.session_state.is_auth:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.title("🔐 Secure Login")
        u_id = st.text_input("Enter Mobile ID", type="password")
        if st.button("Login Now", use_container_width=True):
            if u_id.strip() in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
            else:
                st.error("Invalid ID")
    st.stop()

# ================= 📊 DATA FETCHING (NO SDK NEEDED) =================
# Bhai yahan apni asli keys daal dena
API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"

def get_market_data(index_name):
    # Ye dummy data hai testing ke liye jab tak API connect na ho
    # Asli API integration ke liye yahan requests.get() aayega
    return {"lp": 22450.50, "chg": +0.45}

# ================= ADMIN LOGIC =================
def load_admin():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= UI DESIGN =================
st.sidebar.title("Settings")
idx_choice = st.sidebar.selectbox("Market", ["NIFTY", "SENSEX", "BANKNIFTY"])

data = get_market_data(idx_choice)
sig = load_admin()

# Header
color = "#00FF00" if data['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left:10px solid {color};">
        <h1 style="margin:0; color:white;">{idx_choice}: {data['lp']}</h1>
        <p style="margin:0; color:{color}; font-size:20px;">{data['chg']:+.2f}% | LIVE CONNECTION</p>
    </div>
""", unsafe_allow_html=True)

# Admin Panel
with st.expander("🛠️ Admin Levels"):
    c = st.columns(4)
    v_stk = c[0].text_input("Strike", sig['stk'])
    v_buy = c[1].text_input("Entry", sig['buy'])
    v_tgt = c[2].text_input("Target", sig['tgt'])
    v_sl = c[3].text_input("SL", sig['sl'])
    if st.button("Save Levels"):
        with open(SIG_FILE, "w") as f: 
            json.dump({"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl}, f)
        st.success("Saved!")
        st.rerun()

# Signal Display
st.markdown("---")
cols = st.columns(4)
cols[0].metric("🎯 SIGNAL", sig['stk'])
cols[1].metric("💰 ENTRY", sig['buy'])
cols[2].metric("📈 TARGET", sig['tgt'])
cols[3].metric("📉 STOPLOSS", sig['sl'])

st.info("💡 Bhai, agar ye screen load ho rahi hai toh samajh lo environment sahi hai. Bas ab humein API response format match karna hai.")
