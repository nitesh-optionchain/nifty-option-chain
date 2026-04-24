import streamlit as st
import pandas as pd
from nubra_sdk import NubraClient
from streamlit_autorefresh import st_autorefresh
import json
import os

# ================= 1. PAGE SETUP =================
st.set_page_config(page_title="SMART WEALTH AI", layout="wide", initial_sidebar_state="expanded")

# Auto-refresh har 2 second mein data fetch karne ke liye
st_autorefresh(interval=2000, key="datarefresh")

SIG_FILE = "admin_levels_v2.json"

# ================= 2. SDK CONNECTION (AUTO-FETCH) =================
@st.cache_resource
def get_nubra_client():
    # Bhai, yahan aapki 9304... wali key auto-detect ho jayegi
    return NubraClient(api_key="9304768496")

try:
    nubra = get_nubra_client()
    # Auto-fetch market indices
    nifty = nubra.get_index("NIFTY")
    banknifty = nubra.get_index("BANKNIFTY")
    sensex = nubra.get_index("SENSEX")
    conn_status = "Connected to Live Market ✅"
except Exception as e:
    nifty = banknifty = sensex = {"lp": 0.0, "chg": 0.0}
    conn_status = f"Connecting... ({e})"

# ================= 3. ADMIN DATA LOGIC =================
def load_admin_data():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f:
            return json.load(f)
    return {"stk": "-", "buy": "-", "tgt": "-", "sl": "-"}

admin_sig = load_admin_data()

# ================= 4. DASHBOARD UI =================
st.title("📊 SMART WEALTH AI - TERMINAL")
st.caption(conn_status)

# Top Bar: Live Prices
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("NIFTY 50", f"₹{nifty.get('lp', 0)}", f"{nifty.get('chg', 0)}%")
with c2:
    st.metric("BANKNIFTY", f"₹{banknifty.get('lp', 0)}", f"{banknifty.get('chg', 0)}%")
with c3:
    st.metric("SENSEX", f"₹{sensex.get('lp', 0)}", f"{sensex.get('chg', 0)}%")

st.markdown("---")

# Admin Control Panel
with st.expander("🛠️ ADMIN CONTROL PANEL (Update Signals)"):
    col_a, col_b, col_c, col_d = st.columns(4)
    new_stk = col_a.text_input("Signal Strike", admin_sig['stk'])
    new_buy = col_b.text_input("Entry Price", admin_sig['buy'])
    new_tgt = col_c.text_input("Target", admin_sig['tgt'])
    new_sl = col_d.text_input("Stoploss", admin_sig['sl'])
    
    if st.button("PUSH SIGNAL TO LIVE DASHBOARD", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk": new_stk, "buy": new_buy, "tgt": new_tgt, "sl": new_sl}, f)
        st.success("Signal Updated Successfully!")
        st.rerun()

# Signal Display Area
st.markdown("### 🎯 CURRENT TRADE SIGNAL")
m1, m2, m3, m4 = st.columns(4)
m1.metric("INSTRUMENT", admin_sig['stk'])
m2.metric("ENTRY", admin_sig['buy'])
m3.metric("TARGET", admin_sig['tgt'])
m4.metric("EXIT/SL", admin_sig['sl'])

# Option Chain Matrix
st.markdown("---")
st.subheader("⚡ Live Option Chain Matrix")
try:
    # Auto-fetch Option Chain
    oc_raw = nubra.get_option_chain("NIFTY")
    df_oc = pd.DataFrame(oc_raw)
    st.dataframe(df_oc, use_container_width=True)
except:
    st.info("Waiting for Option Chain stream...")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("System: **Active**")
if st.sidebar.button("Force Re-login"):
    st.cache_resource.clear()
    st.rerun()
