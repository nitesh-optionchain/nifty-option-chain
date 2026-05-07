from __future__ import annotations
import math, os, json, threading, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# ================= 1. CONFIG & PERSISTENCE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
DATA_FILE = "admin_data_v2.json"
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
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

if "is_auth" not in st.session_state: st.session_state.is_auth = False

# --- AUTO-LOGIN RECOVERY ---
if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth = True
        st.session_state.admin_name = ADMIN_DB[saved["user_id"]]
        st.session_state.current_user_id = saved["user_id"]
        st.session_state.is_super_admin = (saved["user_id"] in SUPER_ADMIN_IDS)

if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.current_user_id = user_key
                    st.session_state.is_super_admin = (user_key in SUPER_ADMIN_IDS)
                    save_json(SESSION_FILE, {"user_id": user_key})
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 2. ENGINE & SIDEBAR =================
st_autorefresh(interval=5000, key="v5_ultimate_final_stable")

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        def on_msg(msg):
            name = msg.get('indexname')
            if name and "ticks" in st.session_state: st.session_state.ticks[name] = msg
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: return None

md = get_engine()
if "ticks" not in st.session_state: st.session_state.ticks = {}

# --- PAGE PERSISTENCE ---
matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
saved_idx = matrix_settings.get("last_index", "NIFTY")
default_idx = idx_list.index(saved_idx) if saved_idx in idx_list else 0

with st.sidebar:
    st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
    index_choice = st.selectbox("Select Index", idx_list, index=default_idx)
    if index_choice != saved_idx:
        save_json(SETTINGS_FILE, {"last_index": index_choice})
    
    if st.button("🔒 LOGOUT"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.session_state.clear()
        st.rerun()

target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

# --- ADMIN PANEL ---
if st.session_state.is_super_admin:
    with st.sidebar.expander("👥 User Management"):
        new_uid = st.text_input("Add ID")
        new_uname = st.text_input("Name")
        if st.button("ADD"):
            if new_uid and new_uname:
                ADMIN_DB[new_uid] = new_uname
                save_json(USER_FILE, ADMIN_DB)
                st.rerun()
        u_del = st.selectbox("Remove", [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id])
        if st.button("DELETE"):
            uid_del = u_del.split('(')[-1].replace(')', '')
            del ADMIN_DB[uid_del]
            save_json(USER_FILE, ADMIN_DB)
            st.rerun()

# ================= 3. DASHBOARD RENDER =================
try:
    result = md.option_chain(index_choice, exchange=target_exch)
    if not result or not result.chain:
        st.info("Syncing Market Matrix... ⏳")
        st.stop()

    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    atm = chain.at_the_money_strike / 100
    
    t_idx = st.session_state.ticks.get(index_choice, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)
    cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

    # Header
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"
    st.markdown(f'''<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};">
        <h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">
            {index_choice} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span>
        </h1>
    </div>''', unsafe_allow_html=True)

    # PCR/BEP Strip
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
    st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:10px;">
        <span style="color:#f59e0b;">CE BEP: {atm + 100} {arrow}</span> | 
        <span style="font-size:18px;">PCR: {pcr:.2f} ({mood})</span> | 
        <span style="color:#ef4444;">PE BEP: {atm - 100} {arrow}</span>
    </div>''', unsafe_allow_html=True)

    # DATA PREP
    df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df_comb["STRIKE"] = (df_comb["strike_price"]/100).astype(int)

    # OI Change Stability Fix
    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state: st.session_state[state_key] = df_comb.copy()
    
    def calc_stable_oi(row, side):
        curr_oi = row[f"open_interest_{side}"]
        init_df = st.session_state[state_key].set_index("STRIKE")
        strike = row["STRIKE"]
        return curr_oi - (init_df.loc[strike, f"open_interest_{side}"] if strike in init_df.index else curr_oi)

    df_comb["oi_chg_CE"] = df_comb.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
    df_comb["oi_chg_PE"] = df_comb.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

    # Big Move Prediction
    res_stk = int(df_comb.loc[df_comb[df_comb["STRIKE"] >= live_px]["volume_CE"].idxmax(), "STRIKE"])
    sup_stk = int(df_comb.loc[df_comb[df_comb["STRIKE"] <= live_px]["volume_PE"].idxmax(), "STRIKE"])
    if pcr > 1.25 and live_px >= (res_stk - 30):
        st.success(f"🚀 BIG MOVE: {index_choice} CE BUYING ABOVE {res_stk}")
    elif pcr < 0.75 and live_px <= (sup_stk + 30):
        st.error(f"🩸 BIG MOVE: {index_choice} PE BUYING BELOW {sup_stk}")

    # ================= 4. TABLE UI (3-LINE & ATM PRICE FIX) =================
    max_oi_ce, max_oi_pe = df_comb["open_interest_CE"].max(), df_comb["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df_comb["volume_CE"].max(), df_comb["volume_PE"].max()
    max_chg_ce = df_comb["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df_comb["oi_chg_PE"].abs().max() or 1

    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm_idx = (df_comb["STRIKE"] - live_px).abs().idxmin()
    d_df = df_comb.iloc[max(atm_idx-10,0): atm_idx+11].copy().reset_index(drop=True)

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_CE']:+,}\n{(r['oi_chg_CE']/max_chg_ce*100):.1f}%", axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    
    # --- ATM STRIKE FIX WITH LIVE INDEX ---
    ui["STRIKE"] = d_df["STRIKE"].apply(lambda s: f"⭐ {s} ({arrow}{live_px:,.1f})" if s == atm else str(s))
    
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_PE']:+,}\n{(r['oi_chg_PE']/max_chg_pe*100):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s, idx = [''] * 7, row.name
        stk = d_df.loc[idx, "STRIKE"]
        s[3] = 'background-color:#f8f9fa;color:black;font-weight:bold' 
        if stk == atm: s[3] = 'background-color:yellow;color:black'
        # CE Styling
        if float(row.iloc[0].split('\n')[-1].replace('%','')) >= 70: s[0] = 'background-color:#1565c0;color:white'
        if float(row.iloc[1].split('\n')[-1].replace('%','')) >= 70: s[1] = 'background-color:#2e7d32;color:white'
        if float(row.iloc[2].split('\n')[-1].replace('%','')) >= 75: s[2] = 'background-color:#1b5e20;color:white'
        # PE Styling
        if float(row.iloc[4].split('\n')[-1].replace('%','')) >= 75: s[4] = 'background-color:#b71c1c;color:white'
        if float(row.iloc[5].split('\n')[-1].replace('%','')) >= 70: s[5] = 'background-color:#c62828;color:white'
        if float(row.iloc[6].split('\n')[-1].replace('%','')) >= 70: s[6] = 'background-color:#ef6c00;color:white'
        # Border
        if stk == res_stk: 
            for i in range(7): s[i] += '; border-top: 5px solid blue;'
        if stk == sup_stk: 
            for i in range(7): s[i] += '; border-bottom: 5px solid red;'
        return s

    st.table(ui.style.apply(style_table, axis=1))
except Exception as e:
    st.info(f"Syncing Matrix... {e}")
