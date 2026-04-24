import streamlit as st
import pandas as pd
import threading
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata
from streamlit_autorefresh import st_autorefresh

# ================= 1. SETUP =================
st.set_page_config(page_title="SMART WEALTH AI - LIVE", layout="wide")
st_autorefresh(interval=2000, key="ui_refresh")
IST = ZoneInfo("Asia/Kolkata")
SIG_FILE = "admin_v16_data.json"

# ================= 2. WEBSOCKET ENGINE =================
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
                on_error=lambda e: setattr(self, 'status', "OFFLINE ❌")
            )
            self.socket.connect()
            self.socket.subscribe(["NIFTY", "SENSEX"], data_type="index", exchange="NSE")
        except: self.status = "Error"

    def _on_tick(self, msg):
        with self.lock:
            sym = getattr(msg, "indexname", "")
            raw = getattr(msg, "index_value", 0)
            price = round(raw / 100 if raw > 100000 else raw, 2)
            if sym in self.live_data:
                self.live_data[sym] = {"lp": price, "chg": getattr(msg, "changepercent", 0.0)}

    def get_price(self, idx):
        with self.lock: return self.live_data.get(idx, {"lp":0.0, "chg":0.0})

# ================= 3. MANUAL DATA STORAGE =================
def load_manual_data():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}, 
            "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

if "is_auth" not in st.session_state: st.session_state.is_auth = False
if not st.session_state.is_auth:
    u_id = st.text_input("Mobile ID", type="password")
    if st.button("Login"):
        if u_id in ["9304768496", "7982046438"]:
            st.session_state.is_auth = True
            st.rerun()
    st.stop()

# Persistent Client
if "engine" not in st.session_state:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    st.session_state.engine = MarketEngine(client)
    st.session_state.api = client

# ================= 4. UI & ADMIN PANEL =================
idx_choice = st.sidebar.selectbox("Market", ["NIFTY", "SENSEX"])
live = st.session_state.engine.get_price(idx_choice)
all_sigs = load_manual_data()
sig = all_sigs[idx_choice]

# Header
color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
st.markdown(f"<div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border-left:8px solid {color};'><h2>{idx_choice}: {live['lp']:,} <span style='font-size:18px;'>({live['chg']:+.2f}%)</span></h2></div>", unsafe_allow_html=True)

# --- MANUAL ENTRY SECTION ---
with st.expander("🛠️ ADMIN PANEL (MANUAL ENTRY)"):
    c = st.columns(4)
    v_stk = c[0].text_input("Signal Strike", sig['stk'])
    v_buy = c[1].text_input("Entry Price", sig['buy'])
    v_tgt = c[2].text_input("Target", sig['tgt'])
    v_sl = c[3].text_input("Stoploss", sig['sl'])
    v_sup = st.text_input("Support Strike (For Table)", sig['sup'])
    v_res = st.text_input("Resistance Strike (For Table)", sig['res'])
    if st.button("SAVE LEVELS"):
        all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
        with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
        st.success("Data Updated!")
        st.rerun()

# Display Metrics
m = st.columns(4)
m[0].metric("🎯 SIGNAL", sig['stk']); m[1].metric("💰 BUY", sig['buy'])
m[2].metric("📈 TGT", sig['tgt']); m[3].metric("📉 SL", sig['sl'])

# ================= 5. OPTION CHAIN & COLOUR CODE =================
try:
    res = st.session_state.api.marketdata.option_chain(idx_choice, exchange="NSE" if idx_choice=="NIFTY" else "BSE")
    def parse(d): return pd.DataFrame([{"strike": x.strike_price, "oi": getattr(x, 'open_interest', 0), "vol": getattr(x, 'volume', 0)} for x in d])
    df = pd.merge(parse(res.chain.ce), parse(res.chain.pe), on="strike", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
    mx_oi_ce, mx_vol_ce = df["oi_CE"].max() or 1, df["vol_CE"].max() or 1
    mx_oi_pe, mx_vol_pe = df["oi_PE"].max() or 1, df["vol_PE"].max() or 1
    atm = df.loc[(df["STRIKE"] - live['lp']).abs().idxmin(), "STRIKE"]

    def style_table(row):
        s = [''] * len(row)
        stk = int(row["STRIKE"])
        # 70% Colour Logic
        if (row["oi_CE"] / mx_oi_ce) >= 0.7: s[0] = 'background-color: #E65100; color: white;' # Orange
        if (row["vol_CE"] / mx_vol_ce) >= 0.7: s[1] = 'background-color: #4A148C; color: white;' # Purple
        if (row["oi_PE"] / mx_oi_pe) >= 0.7: s[4] = 'background-color: #E65100; color: white;'
        if (row["vol_PE"] / mx_vol_pe) >= 0.7: s[3] = 'background-color: #4A148C; color: white;'
        # ATM & Manual Levels Highlight
        if stk == atm: s[2] = 'background-color: #FFD600; color: black; font-weight: bold;'
        if str(stk) == sig['sup']: s[2] = 'background-color: #d32f2f; color: white;'
        if str(stk) == sig['res']: s[2] = 'background-color: #388e3c; color: white;'
        return s

    st.subheader("Live Option Chain")
    ui = df[["oi_CE", "vol_CE", "STRIKE", "vol_PE", "oi_PE"]]
    idx_atm = ui.index[ui["STRIKE"] == atm][0]
    st.table(ui.iloc[max(idx_atm-10, 0): idx_atm+11].style.apply(style_table, axis=1))

except: st.info("Loading Option Chain...")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
