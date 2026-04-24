import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & REFRESH =================
st.set_page_config(page_title="SMART WEALTH AI - LIVE", layout="wide")
st_autorefresh(interval=3000, key="live_refresh") # Har 3 second mein refresh
SIG_FILE = "admin_levels_v2.json"

# ================= 2. 🔑 API CREDENTIALS =================
# BHAI: Yahan apni asli keys quotes (" ") ke andar daal dena
API_KEY = "9304768496"
API_SECRET = "3974"

# ================= 3. LIVE DATA FUNCTION =================
def fetch_live_data(index_name):
    try:
        # Nubra API Endpoint (Check documentation for exact URL)
        # NIFTY, BANKNIFTY, SENSEX ke liye dynamic URL
        url = f"https://api.nubra.in/market/index/{index_name}"
        headers = {
            "api-key": API_KEY,
            "api-secret": API_SECRET,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # Note: Agar data keys 'lp' aur 'chg' se alag hain toh yahan badal dena
            return {
                "lp": data.get("last_price", "No Data"),
                "chg": data.get("change_percent", 0.0),
                "status": "LIVE ✅"
            }
        else:
            return {"lp": "Auth Error", "chg": 0.0, "status": f"Error {response.status_code}"}
            
    except Exception as e:
        return {"lp": "Offline", "chg": 0.0, "status": "Connection Fail ❌"}

# ================= 4. ADMIN DATA STORAGE =================
def get_sigs():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= 5. LOGIN LOGIC =================
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if not st.session_state.is_auth:
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.markdown("<br><br><h1 style='text-align:center;'>🔐 Login</h1>", unsafe_allow_html=True)
        u_id = st.text_input("Mobile ID", type="password")
        if st.button("Unlock Dashboard", use_container_width=True):
            if u_id.strip() in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
    st.stop()

# ================= 6. DASHBOARD UI =================
st.sidebar.title("Settings")
idx_choice = st.sidebar.selectbox("Select Market", ["NIFTY", "BANKNIFTY", "SENSEX"])

# Fetching Data
live = fetch_live_data(idx_choice)
sig = get_sigs()

# Main Header
m_color = "#00FF00" if isinstance(live['lp'], (int, float)) and live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:25px; border-radius:15px; border-left:10px solid {m_color};">
        <h1 style="margin:0; color:white; font-size:40px;">{idx_choice}: {live['lp']}</h1>
        <p style="margin:0; color:{m_color}; font-size:20px;">{live['chg']}% | {live['status']}</p>
    </div>
""", unsafe_allow_html=True)

# Admin Panel
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v_stk = c[0].text_input("Signal Strike", sig['stk'])
    v_buy = c[1].text_input("Entry Price", sig['buy'])
    v_tgt = c[2].text_input("Target", sig['tgt'])
    v_sl = c[3].text_input("Stoploss", sig['sl'])
    if st.button("UPDATE LIVE TERMINAL"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl}, f)
        st.success("Levels Updated!")
        st.rerun()

# Professional Metrics
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])

# Option Chain (Dynamic Table)
st.subheader(f"⚡ {idx_choice} Option Chain")
try:
    # Yahan asli option chain fetching logic aayega jab URL mil jayega
    st.info("Waiting for Option Chain API response...")
    # Placeholder Table
    df = pd.DataFrame({"OI CE": [0], "STRIKE": [live['lp']], "OI PE": [0]})
    st.table(df)
except:
    st.error("Option Chain Connection Failed")
