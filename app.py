from __future__ import annotations
import math, os, json, threading, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. SYSTEM & MEMORY =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "ticks" not in st.session_state: st.session_state.ticks = {}
if "is_auth" not in st.session_state: st.session_state.is_auth = False
if "allowed_users" not in st.session_state: st.session_state.allowed_users = ["9304768496", "7982046438"]

# --- 2. ENGINE (CRITICAL FIX FOR GitHub/NoneType Error) ---
st_autorefresh(interval=3000, key="v5_github_fix")

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        
        # GitHub/Streamlit Cloud ke liye env_creds=True hona zaroori hai
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        def on_msg(msg):
            name = msg.get('indexname')
            if name: st.session_state.ticks[name] = msg
            
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        
        return MarketData(nubra)
    except Exception as e:
        # Error ko backend mein store karna taaki user ko dikha sakein
        return str(e) 

md_engine = get_engine()

# --- ADMIN LOGIN CHECK ---
if not st.session_state.is_auth:
    with st.sidebar:
        st.header("🔐 Admin Panel")
        admin_id = st.text_input("Mobile ID")
        key = st.text_input("Secret Key", type="password")
        if st.button("AUTHORIZE"):
            if admin_id in st.session_state.allowed_users and key == "SW@2026":
                st.session_state.is_auth = True
                st.rerun()
    st.info("Login required to access Matrix.")
    st.stop()

# ================= 3. ERROR CHECKING & UI =================
# Agar md_engine string hai, matlab error aaya hai
if isinstance(md_engine, str):
    st.error(f"❌ Connection Error: {md_engine}")
    st.warning("Bhai, Streamlit Cloud ke 'Settings > Secrets' mein apni API Keys check kijiye.")
    st.stop()

# Agar md_engine None hai
if md_engine is None:
    st.warning("⏳ Initializing Engine... Please wait for 5 seconds.")
    st.stop()

# --- MAIN DASHBOARD START ---
INDEX_MAP = {"NIFTY": "NSE", "BANKNIFTY": "NSE", "SENSEX": "BSE"}
symbol = st.sidebar.selectbox("Dashboard", list(INDEX_MAP.keys()))

try:
    res = md_engine.option_chain(symbol, exchange=INDEX_MAP[symbol])
    if res is None or not hasattr(res, 'chain'):
        st.info("Fetching Market Data... ⏳")
        st.stop()

    # (Yahan se niche ka poora logic (Header, Big Move, Table) wahi hai jo maine upar diya tha)
    # ... (Please use the previous Table/Color logic here) ...
    
    chain = res.chain
    # ... rest of the code ...
    st.success("Data Loaded Successfully!") # Proof that engine is working

except Exception as e:
    st.error(f"Matrix Error: {e}")
