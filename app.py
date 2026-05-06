from __future__ import annotations
import math, os, json, threading, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ================= 1. SYSTEM & PERSISTENCE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

STORE_FILE = "matrix_settings.json"

def save_settings(is_auth, last_index, allowed_users):
    with open(STORE_FILE, "w") as f:
        json.dump({"is_auth": is_auth, "last_index": last_index, "allowed_users": allowed_users}, f)

def load_settings():
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r") as f:
                d = json.load(f)
                if "allowed_users" not in d: d["allowed_users"] = ["9304768496", "7982046438"]
                return d
        except: pass
    return {"is_auth": False, "last_index": "NIFTY", "allowed_users": ["9304768496", "7982046438"]}

settings = load_settings()
if "ticks" not in st.session_state: st.session_state.ticks = {}
if "is_auth" not in st.session_state: st.session_state.is_auth = settings.get("is_auth", False)
if "allowed_users" not in st.session_state: st.session_state.allowed_users = settings.get("allowed_users")

# ================= 2. DATA ENGINE =================
st_autorefresh(interval=3000, key="v5_gh_final_stable")

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
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: return None

md = get_engine()

# ================= 3. ADMIN PANEL =================
with st.sidebar:
    st.header("🔐 Admin Control")
    if not st.session_state.is_auth:
        admin_id = st.text_input("Mobile ID")
        key = st.text_input("Secret Key", type="password")
        if st.button("AUTHORIZE"):
            if admin_id in st.session_state.allowed_users and key == "SW@2026":
                st.session_state.is_auth = True
                save_settings(True, settings.get("last_index", "NIFTY"), st.session_state.allowed_users)
                st.rerun()
    else:
        st.success("Authorized ✅")
        st.subheader("👥 User Management")
        new_u = st.text_input("Add Mobile ID")
        if st.button("➕ Add Viewer"):
            if new_u and new_u not in st.session_state.allowed_users:
                st.session_state.allowed_users.append(new_u)
                save_settings(True, settings.get("last_index", "NIFTY"), st.session_state.allowed_users)
                st.rerun()
        u_rem = st.selectbox("Remove User", st.session_state.allowed_users)
        if st.button("❌ Remove Selected"):
            if u_rem not in ["9304768496"]:
                st.session_state.allowed_users.remove(u_rem)
                save_settings(True, settings.get("last_index", "NIFTY"), st.session_state.allowed_users)
                st.rerun()
        if st.button("🚪 LOGOUT"):
            st.session_state.is_auth = False
            if os.path.exists(STORE_FILE): os.remove(STORE_FILE)
            st.rerun()

if not st.session_state.is_auth:
    st.info("Please Login to access Dashboard.")
    st.stop()

# --- MARKET SELECTION & PERSISTENCE ---
INDEX_MAP = {"NIFTY": "NSE", "BANKNIFTY": "NSE", "SENSEX": "BSE"}
idx_list = list(INDEX_MAP.keys())
saved_idx = settings.get("last_index", "NIFTY")
symbol = st.sidebar.selectbox("Dashboard", idx_list, index=idx_list.index(saved_idx) if saved_idx in idx_list else 0)
if symbol != saved_idx: save_settings(True, symbol, st.session_state.allowed_users)

def clean_v(v):
    if v is None: return 0.0
    try:
        val = float(v)
        return val / 100.0 if abs(val) >= 100000 else val
    except: return 0.0

# ================= 4. UI RENDER & LOGIC =================
try:
    if md is None:
        st.error("Engine Connection Failed. Check Secrets/API Key.")
        st.stop()

    res = md.option_chain(symbol, exchange=INDEX_MAP[symbol])
    if res is None or not hasattr(res, 'chain'):
        st.info("Synchronizing Market Matrix... ⏳")
        st.stop()

    chain = res.chain
    spot, atm = clean_v(chain.current_price), clean_v(chain.at_the_money_strike)
    
    t_idx = st.session_state.ticks.get(symbol, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)
    cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

    # LIGHT HEADER
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"

    st.markdown(f'''<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};">
        <h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">
            {symbol} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span>
        </h1>
    </div>''', unsafe_allow_html=True)

    # --- S/R CALCULATION (INDEX-CENTRIC) ---
    full_ce = pd.DataFrame([vars(x) for x in chain.ce])
    full_pe = pd.DataFrame([vars(x) for x in chain.pe])
    m_df = pd.merge(full_ce, full_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    m_df["STRK"] = (m_df["strike_price"]/100).astype(int)

    active_zone = m_df[(m_df["STRK"] >= live_px - 500) & (m_df["STRK"] <= live_px + 500)]
    res_stk = int(active_zone.loc[active_zone["volume_CE"].idxmax(), "STRK"])
    sup_stk = int(active_zone.loc[active_zone["volume_PE"].idxmax(), "STRK"])

    # PCR & STRIP
    t_ce_oi = full_ce["open_interest"].sum() or 1
    t_pe_oi = full_pe["open_interest"].sum() or 1
    pcr = t_pe_oi / t_ce_oi
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"

    st.markdown(f'''<div style="background:#f8fafc; color:#334155; padding:8px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:8px;">
        <span style="color:#0d47a1;">RESISTANCE (Near Index): {res_stk}</span> | 
        <span style="font-size:16px;">PCR: {pcr:.2f} ({mood})</span> | 
        <span style="color:#b71c1c;">SUPPORT (Near Index): {sup_stk}</span>
    </div>''', unsafe_allow_html=True)

    # --- BIG MOVE PREDICTION ---
    pred_msg, pred_color = "", ""
    if pcr < 0.75 and live_px <= (sup_stk + 35):
        pred_msg = f"🩸 BIG MOVE: {symbol} PE BUYING BELOW {sup_stk}"
        pred_color = "#b71c1c"
    elif pcr > 1.25 and live_px >= (res_stk - 35):
        pred_msg = f"🚀 BIG MOVE: {symbol} CE BUYING ABOVE {res_stk}"
        pred_color = "#1b5e20"
    
    if pred_msg:
        st.markdown(f'''<div style="background:{pred_color}; color:white; padding:12px; border-radius:5px; text-align:center; font-size:22px; font-weight:bold; margin:10px 0; border: 2px solid black;">{pred_msg}</div>''', unsafe_allow_html=True)

    # --- TABLE RENDERING ---
    idx_row = (m_df["STRK"] - live_px).abs().idxmin()
    v_df = m_df.iloc[max(0, idx_row-8):idx_row+9].reset_index(drop=True)
    
    mx_v_ce, mx_v_pe = active_zone["volume_CE"].max() or 1, active_zone["volume_PE"].max() or 1
    mx_o_ce, mx_o_pe = active_zone["open_interest_CE"].max() or 1, active_zone["open_interest_PE"].max() or 1

    def f_oi_chg(curr, prev, base):
        diff = curr - prev
        p = (diff / base * 100) if base > 0 else 0.0
        return f"{diff:+,.0f} ({p:+.1f}%)"

    ui = pd.DataFrame()
    ui["CE OI (%)"] = v_df.apply(lambda r: f"{r['open_interest_CE']:,.0f} ({(r['open_interest_CE']/mx_o_ce)*100:.1f}%)", axis=1)
    ui["CE OI CHG (%)"] = v_df.apply(lambda r: f_oi_chg(r["open_interest_CE"], r["previous_open_interest_CE"], mx_o_ce), axis=1)
    ui["CE VOL (%)"] = v_df.apply(lambda r: f"{r['volume_CE']:,.0f} ({(r['volume_CE']/mx_v_ce)*100:.1f}%)", axis=1)
    ui["STRIKE"] = v_df["STRK"].apply(lambda s: f"⭐ {s} ({arrow}{live_px:,.1f})" if s == atm else str(s))
    ui["PE VOL (%)"] = v_df.apply(lambda r: f"{r['volume_PE']:,.0f} ({(r['volume_PE']/mx_v_pe)*100:.1f}%)", axis=1)
    ui["PE OI CHG (%)"] = v_df.apply(lambda r: f_oi_chg(r["open_interest_PE"], r["previous_open_interest_PE"], mx_o_pe), axis=1)
    ui["PE OI (%)"] = v_df.apply(lambda r: f"{r['open_interest_PE']:,.0f} ({(r['open_interest_PE']/mx_o_pe)*100:.1f}%)", axis=1)

    def style_table(row):
        s, orig = [''] * 7, v_df.iloc[row.name]
        stk = orig["STRK"]
        s[3] = 'background-color: #f8f9fa; color: black; font-weight: bold;'
        if stk == atm: s[3] = 'background-color: #fbc02d; border: 2px solid black;'
        
        # CE/PE Color Logic
        if orig["volume_CE"] >= mx_v_ce * 0.95: s[2] = 'background-color: #1b5e20; color: white;' 
        elif (orig["volume_CE"]/mx_v_ce) >= 0.70: s[2] = 'background-color: #c8e6c9; color: black;'
        if (orig["open_interest_CE"]/mx_o_ce) >= 0.70: s[0] = s[1] = 'background-color: #ffcc80; color: black;' 
        
        if orig["volume_PE"] >= mx_v_pe * 0.95: s[4] = 'background-color: #b71c1c; color: white;' 
        elif (orig["volume_PE"]/mx_v_pe) >= 0.70: s[4] = 'background-color: #ffcdd2; color: black;'
        if (orig["open_interest_PE"]/mx_o_pe) >= 0.70: s[5] = s[6] = 'background-color: #f8bbd0; color: black;' 

        # Border Lines (Corrected Syntax)
        if stk == res_stk: 
            for i in range(7): s[i] += '; border-top: 6px solid #0d47a1;'
        if stk == sup_stk: 
            for i in range(7): s[i] += '; border-bottom: 6px solid #b71c1c;'
        return s

    st.table(ui.style.apply(style_table, axis=1))

except Exception as e:
    st.info(f"Connecting to Matrix... {e}")
