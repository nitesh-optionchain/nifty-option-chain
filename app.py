from __future__ import annotations
import math, os, json, threading, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & PERSISTENCE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
SETTINGS_FILE = "matrix_settings.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: json.dump(data_to_save, f, indent=4)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
if "is_auth" not in st.session_state: st.session_state.is_auth = False

# --- AUTO-LOGIN ---
if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth, st.session_state.admin_name = True, ADMIN_DB[saved["user_id"]]
        st.session_state.current_user_id, st.session_state.is_super_admin = saved["user_id"], (saved["user_id"] in ["9304768496", "7982046438"])

if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            u_key = st.text_input("Mobile ID", type="password")
            if st.form_submit_button("LOGIN"):
                if u_key in ADMIN_DB:
                    st.session_state.is_auth, st.session_state.admin_name = True, ADMIN_DB[u_key]
                    st.session_state.is_super_admin = (u_key in ["9304768496", "7982046438"])
                    save_json(SESSION_FILE, {"user_id": u_key})
                    st.rerun()
    st.stop()

# ================= 2. OPTIMIZED ENGINE =================
# Refresh rate ko thoda balance kiya hai (3s) taaki blank screen na aaye
st_autorefresh(interval=3000, key="v5_speed_fix")

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        def on_msg(msg):
            name = msg.get('indexname')
            if name: st.session_state.ticks[name] = msg
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "BANKNIFTY", "SENSEX"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: return None

md = get_engine()
if "ticks" not in st.session_state: st.session_state.ticks = {}

# Persistence
m_set = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
sel_idx = st.sidebar.selectbox("Dashboard", idx_list, index=idx_list.index(m_set.get("last_index", "NIFTY")))
if sel_idx != m_set.get("last_index"): save_json(SETTINGS_FILE, {"last_index": sel_idx})

if st.sidebar.button("🔒 LOGOUT"):
    if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
    st.session_state.clear()
    st.rerun()

# ================= 3. FAST RENDERING LOGIC =================
try:
    target_exch = "BSE" if sel_idx == "SENSEX" else "NSE"
    result = md.option_chain(sel_idx, exchange=target_exch)
    
    if not result or not result.chain:
        st.warning(f"🔄 Connecting to {sel_idx} Matrix... Please wait.")
        st.stop()

    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    atm = chain.at_the_money_strike / 100
    
    t_idx = st.session_state.ticks.get(sel_idx, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    chg = (live_px - spot)
    
    # Header & PCR
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if chg >= 0 else ("#ffebee", "#b71c1c")
    st.markdown(f'''<div style="background:{h_bg}; padding:12px; border-radius:10px; text-align:center; border: 2px solid {h_txt};">
        <h2 style="color:{h_txt}; margin:0;">{sel_idx} {"▲" if chg >= 0 else "▼"} {live_px:,.2f} ({chg:+,.2f})</h2>
    </div>''', unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    
    st.markdown(f'''<div style="background:#f8fafc; padding:8px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:8px;">
        CE BEP: {atm + 100} | PCR: {pcr:.2f} | PE BEP: {atm - 100}
    </div>''', unsafe_allow_html=True)

    # Data Processing
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRK"] = (df["strike_price"]/100).astype(int)

    # OI Change (Stable Reference)
    s_key = f"init_{sel_idx}"
    if s_key not in st.session_state: st.session_state[s_key] = df.copy()
    
    def get_oi_chg(r, side):
        curr = r[f"open_interest_{side}"]
        init = st.session_state[s_key].set_index("STRK")
        return curr - (init.loc[r["STRK"], f"open_interest_{side}"] if r["STRK"] in init.index else curr)

    df["oi_chg_CE"] = df.apply(lambda r: get_oi_chg(r, "CE"), axis=1)
    df["oi_chg_PE"] = df.apply(lambda r: get_oi_chg(r, "PE"), axis=1)

    # S/R & Big Move
    res_stk = int(df.loc[df[df["STRK"] >= live_px]["volume_CE"].idxmax(), "STRK"])
    sup_stk = int(df.loc[df[df["STRK"] <= live_px]["volume_PE"].idxmax(), "STRK"])

    if pcr > 1.25 and live_px >= (res_stk - 30): st.success(f"🚀 BIG MOVE: {sel_idx} BUY ABOVE {res_stk}")
    elif pcr < 0.75 and live_px <= (sup_stk + 30): st.error(f"🩸 BIG MOVE: {sel_idx} SELL BELOW {sup_stk}")

    # Table
    mx_o_ce, mx_o_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    mx_v_ce, mx_v_pe = df["volume_CE"].max(), df["volume_PE"].max()
    
    atm_idx = (df["STRK"] - live_px).abs().idxmin()
    v_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy().reset_index(drop=True)

    def fmt(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100) if m>0 else 0:.1f}%"

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = v_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], mx_o_ce), axis=1)
    ui["CE VOL\n(%)"] = v_df.apply(lambda r: fmt(r["volume_CE"], 0, mx_v_ce), axis=1)
    ui["STRIKE"] = v_df["STRK"].apply(lambda s: f"⭐ {s} ({live_px:,.1f})" if s == atm else str(s))
    ui["PE VOL\n(%)"] = v_df.apply(lambda r: fmt(r["volume_PE"], 0, mx_v_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = v_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], mx_o_pe), axis=1)

    def style(row):
        s, stk = [''] * 5, v_df.loc[row.name, "STRK"]
        s[2] = 'background-color:yellow;color:black' if stk == atm else 'background-color:#f8f9fa'
        if stk == res_stk: s = [x + '; border-top: 4px solid blue' for x in s]
        if stk == sup_stk: s = [x + '; border-bottom: 4px solid red' for x in s]
        return s

    st.table(ui.style.apply(style, axis=1))

except Exception as e:
    st.info("🔄 Refreshing Data Matrix...")
