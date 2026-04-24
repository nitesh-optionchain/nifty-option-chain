import os
import sys
import json
import threading
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

# 1. PATH FIX FOR NUBRA SDK
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    from nubra_python_sdk.ticker import websocketdata
except ImportError:
    st.error("❌ SDK folder missing or dependencies not installed!")

# ================= CONFIG & REFRESH =================
st.set_page_config(page_title="SMART WEALTH AI - LIVE", layout="wide")
st_autorefresh(interval=2000, key="ui_refresh_counter") 
IST = ZoneInfo("Asia/Kolkata")
SIG_FILE = "admin_data_v18.json"

# ================= WEBSOCKET ENGINE =================
class MarketEngine:
    def __init__(self, client):
        self.client = client
        self.lock = threading.RLock()
        self.live_data = {"NIFTY": {"lp": 0.0, "chg": 0.0}, "SENSEX": {"lp": 0.0, "chg": 0.0}}
        self.status = "Connecting..."
        self._start_socket()

    def _start_socket(self):
        try:
            self.socket = websocketdata.NubraDataSocket(
                client=self.client,
                on_index_data=self._on_tick,
                on_connect=lambda m: setattr(self, 'status', "LIVE ✅"),
                on_error=lambda e: setattr(self, 'status', f"OFFLINE ❌")
            )
            self.socket.connect()
            self.socket.subscribe(["NIFTY", "SENSEX"], data_type="index", exchange="NSE")
        except: self.status = "Error"

    def _on_tick(self, msg):
        with self.lock:
            sym = getattr(msg, "indexname", "")
            raw = getattr(msg, "index_value", 0)
            # Formatting Price (Scaling fix for Nifty/Sensex)
            price = round(raw / 100 if raw > 100000 else raw, 2)
            if sym in self.live_data:
                self.live_data[sym] = {"lp": price, "chg": getattr(msg, "changepercent", 0.0)}

    def get_live(self, idx):
        with self.lock: return self.live_data.get(idx, {"lp": 0.0, "chg": 0.0})

# ================= AUTHENTICATION =================
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if not st.session_state.is_auth:
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Login Dashboard")
        u_id = st.text_input("Enter Mobile ID", type="password", help="Use your registered mobile number")
        
        if st.button("Unlock Dashboard", use_container_width=True):
            allowed_ids = ["9304768496"]
            if u_id.strip() in allowed_ids:
                st.session_state.is_auth = True
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("❌ Access Denied: Invalid ID")
    st.stop()

# ================= API CONNECTION =================
if "engine" not in st.session_state:
    try:
        # Note: Ye tabhi chalega jab Streamlit Secrets mein API_KEY and API_SECRET honge
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state.engine = MarketEngine(client)
        st.session_state.api = client
    except Exception as e:
        st.error(f"Critical API Error: {e}")
        st.stop()

# ================= DASHBOARD UI =================
engine = st.session_state.engine
api = st.session_state.api

# DATA PERSISTENCE FOR MANUAL ENTRIES
def get_manual():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}, 
            "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

idx_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
live = engine.get_live(idx_choice)
all_sigs = get_manual()
sig = all_sigs[idx_choice]

# HEADER CARD
m_color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left:10px solid {m_color}; margin-bottom:20px;">
        <h1 style="margin:0; color:white; font-size:35px;">{idx_choice}: {live['lp']:,}</h1>
        <p style="margin:0; color:{m_color}; font-size:20px;">{live['chg']:+.2f}% | Status: {engine.status}</p>
    </div>
""", unsafe_allow_html=True)

# ADMIN PANEL
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c = st.columns(4)
    v_stk = c[0].text_input("Signal Strike", sig['stk'])
    v_buy = c[1].text_input("Buy Price", sig['buy'])
    v_tgt = c[2].text_input("Target", sig['tgt'])
    v_sl = c[3].text_input("SL", sig['sl'])
    v_sup = st.text_input("Support Strike (Table Highlight)", sig['sup'])
    v_res = st.text_input("Resistance Strike (Table Highlight)", sig['res'])
    if st.button("UPDATE MARKET DATA"):
        all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
        with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
        st.rerun()

# METRICS
col_m = st.columns(4)
col_m[0].metric("🎯 SIGNAL", sig['stk'])
col_m[1].metric("💰 ENTRY", sig['buy'])
col_m[2].metric("📈 TARGET", sig['tgt'])
col_m[3].metric("📉 STOPLOSS", sig['sl'])

# OPTION CHAIN
st.markdown("---")
try:
    oc_res = api.marketdata.option_chain(idx_choice, exchange="NSE" if idx_choice=="NIFTY" else "BSE")
    
    def parse_oc(data):
        return pd.DataFrame([{"strike": x.strike_price, "oi": getattr(x, 'open_interest', 0), "vol": getattr(x, 'volume', 0)} for x in data])
    
    df_ce = parse_oc(oc_res.chain.ce)
    df_pe = parse_oc(oc_res.chain.pe)
    df = pd.merge(df_ce, df_pe, on="strike", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
    # Heatmap Values
    mx_oi_ce, mx_vol_ce = df["oi_CE"].max() or 1, df["vol_CE"].max() or 1
    mx_oi_pe, mx_vol_pe = df["oi_PE"].max() or 1, df["vol_PE"].max() or 1
    atm = df.loc[(df["STRIKE"] - live['lp']).abs().idxmin(), "STRIKE"]

    def style_chain(row):
        s = [''] * len(row)
        stk = int(row["STRIKE"])
        # 70% Logic
        if (row["oi_CE"] / mx_oi_ce) >= 0.7: s[0] = 'background-color: #E65100; color: white;' # Orange
        if (row["vol_CE"] / mx_vol_ce) >= 0.7: s[1] = 'background-color: #4A148C; color: white;' # Purple
        if (row["oi_PE"] / mx_oi_pe) >= 0.7: s[4] = 'background-color: #E65100; color: white;'
        if (row["vol_PE"] / mx_vol_pe) >= 0.7: s[3] = 'background-color: #4A148C; color: white;'
        # ATM & Manual Highlighting
        if stk == atm: s[2] = 'background-color: #FFD600; color: black; font-weight: bold; border: 2px solid white;'
        if str(stk) == sig['sup']: s[2] = 'background-color: #d32f2f; color: white; border: 2px solid white;'
        if str(stk) == sig['res']: s[2] = 'background-color: #388e3c; color: white; border: 2px solid white;'
        return s

    st.subheader(f"⚡ Live Option Chain: {idx_choice}")
    ui_df = df[["oi_CE", "vol_CE", "STRIKE", "vol_PE", "oi_PE"]]
    idx_atm = ui_df.index[ui_df["STRIKE"] == atm][0]
    st.table(ui_df.iloc[max(idx_atm-10, 0): idx_atm+11].style.apply(style_chain, axis=1))

except Exception as e:
    st.info("🔄 Refreshing Option Chain Data...")

# FOOTER
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
