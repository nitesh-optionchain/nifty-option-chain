import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# ================= 1. SETUP & CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="live_refresh") 
SIG_FILE = "admin_levels_v2.json"

# --- BHAI YAHAN APNI KEYS DAALEIN (Quotes ke andar) ---
API_KEY = "9304768496" 
API_SECRET = "3974"

# ================= 2. DATA LOGIC (ASLI API) =================
def get_market_data(index_name):
    # Base prices for testing - Jab API response aayega ye replace ho jayenge
    prices = {
        "NIFTY": 22450.50,
        "BANKNIFTY": 48200.20,
        "SENSEX": 73800.10
    }
    # Yahan hum requests.get use karenge asli data ke liye
    # headers = {"api-key": API_KEY, "api-secret": API_SECRET}
    # res = requests.get(f"https://api.nubra.in/market/{index_name}", headers=headers)
    
    lp = prices.get(index_name, 0.0)
    return {"lp": lp, "chg": +0.45}

def get_sigs():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"stk":"-","buy":"-","tgt":"-","sl":"-"}

# ================= 3. LOGIN LOGIC =================
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

# ================= 4. DASHBOARD UI =================
idx_choice = st.sidebar.selectbox("Select Market", ["NIFTY", "BANKNIFTY", "SENSEX"])
data = get_market_data(idx_choice)
sig = get_sigs()

# Header
color = "#00FF00" if data['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left:10px solid {color};">
        <h1 style="margin:0; color:white; font-size:40px;">{idx_choice}: {data['lp']:,}</h1>
        <p style="margin:0; color:{color}; font-size:22px;">{data['chg']:+.2f}% | LIVE CONNECTION ✅</p>
    </div>
""", unsafe_allow_html=True)

# Admin Panel
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v_stk = c[0].text_input("Strike", sig['stk'])
    v_buy = c[1].text_input("Entry", sig['buy'])
    v_tgt = c[2].text_input("Target", sig['tgt'])
    v_sl = c[3].text_input("SL", sig['sl'])
    if st.button("UPDATE DATA"):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl}, f)
        st.rerun()

# Metrics
st.markdown("---")
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk'])
m[1].metric("💰 ENTRY", sig['buy'])
m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 STOPLOSS", sig['sl'])

# Option Chain Matrix (Table)
st.subheader(f"⚡ {idx_choice} Option Chain Matrix")
# Ye dummy table hai, asli data API se aayega
df = pd.DataFrame({
    "OI CE": [1200, 1500, 2000, 1800],
    "Vol CE": [5000, 7000, 9000, 6000],
    "STRIKE": [22400, 22450, 22500, 22550],
    "Vol PE": [4000, 8000, 5000, 3000],
    "OI PE": [1100, 1900, 1400, 1000]
})
st.table(df)
