import streamlit as st
import pandas as pd
import threading
import json, os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

# Safely import Nubra (In case of installation issues)
try:
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    from nubra_python_sdk.ticker import websocketdata
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# ================= 1. CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
st_autorefresh(interval=3000, key="global_refresh")
IST = ZoneInfo("Asia/Kolkata")
SIG_FILE = "admin_v17_data.json"

# ================= 2. WEBSOCKET ENGINE (SAFE) =================
class MarketEngine:
    def __init__(self, client):
        self.client = client
        self.lock = threading.RLock()
        self.live_data = {"NIFTY": {"lp": 0.0, "chg": 0.0}, "SENSEX": {"lp": 0.0, "chg": 0.0}}
        self.status = "Initializing..."
        self._start_socket()

    def _start_socket(self):
        try:
            self.socket = websocketdata.NubraDataSocket(
                client=self.client,
                on_index_data=self._on_tick,
                on_connect=lambda m: setattr(self, 'status', "LIVE ✅"),
                on_error=lambda e: setattr(self, 'status', f"OFFLINE: {e}")
            )
            self.socket.connect()
            self.socket.subscribe(["NIFTY", "SENSEX"], data_type="index", exchange="NSE")
        except Exception as e:
            self.status = f"Socket Error: {e}"

    def _on_tick(self, msg):
        with self.lock:
            sym = getattr(msg, "indexname", "")
            raw = getattr(msg, "index_value", 0)
            price = round(raw / 100 if raw > 100000 else raw, 2)
            if sym in self.live_data:
                self.live_data[sym] = {"lp": price, "chg": getattr(msg, "changepercent", 0.0)}

    def get_price(self, idx):
        with self.lock: return self.live_data.get(idx, {"lp":0.0, "chg":0.0})

# ================= 3. UI HELPERS =================
def load_manual_data():
    try:
        if os.path.exists(SIG_FILE):
            with open(SIG_FILE, "r") as f: return json.load(f)
    except: pass
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}, 
            "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

# ================= 4. MAIN APP =================
def main():
    if not SDK_AVAILABLE:
        st.error("❌ Nubra SDK ya aiohttp install nahi hua hai. Requirements.txt check karein.")
        st.stop()

    if "is_auth" not in st.session_state: st.session_state.is_auth = False
    
    if not st.session_state.is_auth:
        st.title("🔐 Login")
        u_id = st.text_input("Mobile ID", type="password")
        if st.button("Login"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
        st.stop()

    # Connection Persistence
    if "engine" not in st.session_state:
        try:
            # Check for secrets or env
            client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
            st.session_state.engine = MarketEngine(client)
            st.session_state.api = client
        except Exception as e:
            st.error(f"❌ Connection Fail: {e}. Please check your API Keys in Streamlit Secrets.")
            st.stop()

    idx_choice = st.sidebar.selectbox("Market", ["NIFTY", "SENSEX"])
    live = st.session_state.engine.get_price(idx_choice)
    all_sigs = load_manual_data()
    sig = all_sigs[idx_choice]

    # --- UI Display ---
    color = "#00FF00" if live['chg'] >= 0 else "#FF4B4B"
    st.markdown(f"<div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border-left:8px solid {color};'><h2>{idx_choice}: {live['lp']:,} <span style='font-size:18px;'>({live['chg']:+.2f}%)</span></h2></div>", unsafe_allow_html=True)

    # Admin Panel
    with st.expander("🛠️ ADMIN PANEL"):
        c = st.columns(4)
        v_stk = c[0].text_input("Strike", sig['stk'])
        v_buy = c[1].text_input("Buy", sig['buy'])
        v_tgt = c[2].text_input("Tgt", sig['tgt'])
        v_sl = c[3].text_input("SL", sig['sl'])
        v_sup = st.text_input("Support Strike", sig['sup'])
        v_res = st.text_input("Resistance Strike", sig['res'])
        if st.button("Update Data"):
            all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
            with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
            st.rerun()

    # Metrics
    col_m = st.columns(4)
    col_m[0].metric("SIGNAL", sig['stk'])
    col_m[1].metric("BUY", sig['buy'])
    col_m[2].metric("TARGET", sig['tgt'])
    col_m[3].metric("SL", sig['sl'])

    # Option Chain (Wrap in Try-Except to prevent crash)
    try:
        res = st.session_state.api.marketdata.option_chain(idx_choice, exchange="NSE" if idx_choice=="NIFTY" else "BSE")
        # ... (Wahi styling logic jo pehle tha)
        st.success("Option Chain Live")
    except Exception as e:
        st.info(f"Waiting for Option Chain... ({e})")

if __name__ == "__main__":
    main()
