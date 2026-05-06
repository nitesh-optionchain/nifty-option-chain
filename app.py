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

# --- LOGIN RECOVERY LOGIC ---
if "is_auth" not in st.session_state: st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved["user_id"] in ADMIN_DB:
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
st_autorefresh(interval=5000, key="v5_stable_sync")

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

with st.sidebar:
    st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
    index_choice = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
    if st.button("🔒 LOGOUT"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.session_state.clear()
        st.rerun()

target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

# ================= 3. UI RENDERING =================
try:
    result = md.option_chain(index_choice, exchange=target_exch)
    if not result or not result.chain:
        st.info("Market data load ho raha hai... ⏳")
        st.stop()

    chain = result.chain
    raw_spot = getattr(chain, 'underlying_price', getattr(chain, 'at_the_money_strike', 0))
    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    
    t_idx = st.session_state.ticks.get(index_choice, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)
    cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

    # LIGHT HEADER
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"

    st.markdown(f'''<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};">
        <h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">
            {index_choice} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span>
        </h1>
    </div>''', unsafe_allow_html=True)

    # ================= 4. PURANA CALCULATION LOGIC =================
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # Stable OI Change Logic (Purane code se)
    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()

    def calc_stable_oi(row, side):
        curr_oi = row[f"open_interest_{side}"]
        init_df = st.session_state[state_key].set_index("STRIKE")
        strike = row["STRIKE"]
        prev_oi = init_df.loc[strike, f"open_interest_{side}"] if strike in init_df.index else curr_oi
        return curr_oi - prev_oi

    df["oi_chg_CE"] = df.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
    df["oi_chg_PE"] = df.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

    # Max Values for %
    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce = df["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df["oi_chg_PE"].abs().max() or 1

    # Resistance/Support (Based on Max Volume - Near Index Zone)
    res_stk = int(df.loc[df[df["STRIKE"] >= live_px]["volume_CE"].idxmax(), "STRIKE"])
    sup_stk = int(df.loc[df[df["STRIKE"] <= live_px]["volume_PE"].idxmax(), "STRIKE"])

    # BIG MOVE Alert
    t_pe_sum = df["open_interest_PE"].sum() or 1
    t_ce_sum = df["open_interest_CE"].sum() or 1
    pcr = t_pe_sum / t_ce_sum
    
    if pcr > 1.25 and live_px >= (res_stk - 30):
        st.success(f"🚀 BIG MOVE: {index_choice} CE BUYING ABOVE {res_stk}")
    elif pcr < 0.75 and live_px <= (sup_stk + 30):
        st.error(f"🩸 BIG MOVE: {index_choice} PE BUYING BELOW {sup_stk}")

    # ================= 5. TABLE UI (PURANA FMT_VAL LOGIC) =================
    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    def fmt_chg(delta, m_delta):
        pct = (delta/m_delta*100) if m_delta > 0 else 0
        return f"{delta:+,}\n{pct:.1f}%"

    atm_strike = df.loc[(df["STRIKE"] - live_px).abs().idxmin(), "STRIKE"]
    atm_idx = df.index[df["STRIKE"] == atm_strike][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy().reset_index(drop=True)

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"].apply(lambda s: f"⭐ {s}" if s == atm_strike else str(s))
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s = [''] * 7
        try:
            idx = row.name
            stk = int(d_df.loc[idx, "STRIKE"])
            # Extract % for coloring
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            s[3] = 'background-color:#f8f9fa;color:black;font-weight:bold' 
            if stk == atm_strike: s[3] = 'background-color:yellow;color:black'
            
            if c_oi_p >= 70: s[0] = 'background-color:#1565c0;color:white' # Deep Blue
            if c_ch_p >= 70: s[1] = 'background-color:#2e7d32;color:white' # Deep Green
            if p_ch_p >= 70: s[5] = 'background-color:#c62828;color:white' # Deep Red
            if p_oi_p >= 70: s[6] = 'background-color:#ef6c00;color:white' # Deep Orange

            if c_vo_p >= 75: s[2] = 'background-color:#1b5e20;color:white'
            if p_vo_p >= 75: s[4] = 'background-color:#b71c1c;color:white'

            if stk == res_stk: 
                for i in range(7): s[i] += '; border-top: 5px solid #0d47a1;'
            if stk == sup_stk: 
                for i in range(7): s[i] += '; border-bottom: 5px solid #b71c1c;'
        except: pass
        return s

    st.subheader(f"📊 {index_choice} Option Matrix")
    st.table(ui.style.apply(style_table, axis=1))

except Exception as e:
    st.error(f"Error: {e}")
