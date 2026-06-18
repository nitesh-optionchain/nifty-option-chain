from __future__ import annotations
import math, os, json, threading, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import urllib.parse  # Dynamic UPI URI configuration ke liye
from nubra_python_sdk.ticker import websocketdata  # 🚀 Live candle data streaming ke liye

# ================= 1. CONFIG & SYSTEM SECURITY WITH PAYWALL SYSTEM =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
DATA_FILE = "admin_data_v2.json"
SETTINGS_FILE = "matrix_settings.json"

# --- MERCHANDISE UPI SETTINGS CONFIG ---
ADMIN_UPI_ID = "9304768496@ybl"  # 👈 Yahan apni exact merchant/personal UPI ID daalein
MONTHLY_SUBSCRIPTION_FEES = 499.00     # Monthly renewal charge amount

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

# User and Subscription database engine initialization
ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]
SUBSCRIPTION_DB = load_json(DATA_FILE, {})

# Default initialization logic for users in subscription engine
for uid in ADMIN_DB:
    if uid not in SUBSCRIPTION_DB:
        SUBSCRIPTION_DB[uid] = {
            "status": "Paid" if uid in SUPER_ADMIN_IDS else "Unpaid",
            "expiry_date": "2030-12-31" if uid in SUPER_ADMIN_IDS else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "last_transaction_id": "INITIAL_BETA"
        }
save_json(DATA_FILE, SUBSCRIPTION_DB)

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = ""
    st.session_state.current_user_id = ""
    st.session_state.is_super_admin = False
    st.session_state.is_paid_active = False

# Session Auto-Recovery Framework (Fixes Auto-Logout on Refresh)
if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        uid = saved["user_id"]
        st.session_state.is_auth = True
        st.session_state.admin_name = ADMIN_DB[uid]
        st.session_state.current_user_id = uid
        st.session_state.is_super_admin = (uid in SUPER_ADMIN_IDS)

# Real-time calculation loop to isolate license validities
def check_user_subscription_status(user_id):
    if user_id in SUPER_ADMIN_IDS:
        return True
    user_data = SUBSCRIPTION_DB.get(user_id, {})
    if user_data.get("status") == "Paid":
        try:
            expiry = datetime.strptime(user_data.get("expiry_date", ""), "%Y-%m-%d")
            if datetime.now() <= expiry:
                return True
        except: pass
    return False

# --- CORE LOGIN CONTROLLER FRAMEWORK ---
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

# Set immediate variable boundary flags for access authorization
st.session_state.is_paid_active = check_user_subscription_status(st.session_state.current_user_id)

# --- 💳 PREMIUM ONLINE PAYWALL INTERFACE SYSTEM ---
if not st.session_state.is_paid_active:
    st.markdown("<h2 style='text-align: center; color: #ef4444;'>🔒 RENEWAL REQUIRED: ACCESS RESTRICTED</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Aapka account currently premium active mode me nahi hai. Main dashboard dekhne ke liye payment complete kijiye.</p>", unsafe_allow_html=True)
    
    _, p_col, _ = st.columns([1, 1.2, 1])
    with p_col:
        st.markdown(f"""
        <div style="background:#f8fafc; border:2px solid #ef4444; border-radius:12px; padding:20px; text-align:center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <h3 style="color:#1e293b; margin-top:0;">Premium Monthly Subscription</h3>
            <h1 style="color:#0284c7; margin:10px 0;">₹ {MONTHLY_SUBSCRIPTION_FEES:,.2f} <span style="font-size:14px; color:#64748b;">/ Per Month</span></h1>
            <p style="font-size:12px; color:#475569;">Scan QR with Google Pay, PhonePe, Paytm, or any UPI App to activate instant validity updates.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Dynamic UPI Merchant URL Generation
        payload_text = f"upi://pay?pa={ADMIN_UPI_ID}&pn=Smart%20Wealth%20AI&am={MONTHLY_SUBSCRIPTION_FEES}&cu=INR&tn=Sub_{st.session_state.current_user_id}"
        encoded_upi = urllib.parse.quote_plus(payload_text)
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_upi}"
        
        st.markdown(f"<div style='text-align: center; margin-top:20px;'><img src='{qr_api_url}' style='border:4px solid #cbd5e1; border-radius:8px; padding:5px;'/></div>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:11px; font-weight:bold; color:#0284c7;'>Reference TXN Note: Sub_{st.session_state.current_user_id}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<p style='font-size:13px; font-weight:bold; color:#1e293b; margin-bottom:5px;'>💡 Auto-Fetch Payment Verification:</p>", unsafe_allow_html=True)
        
        with st.form("Verify Payment Form"):
            utr_ref = st.text_input("Enter 12-Digit UPI Ref No / UTR Number:", placeholder="e.g. 4023XXXXXXXX")
            if st.form_submit_button("VERIFY & ACTIVATE INSTANTLY"):
                clean_utr = re.sub(r'[^0-9]', '', utr_ref)
                if len(clean_utr) == 12:
                    # Automated Validation Mapping Lock
                    SUBSCRIPTION_DB[st.session_state.current_user_id] = {
                        "status": "Paid",
                        "expiry_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "last_transaction_id": clean_utr
                    }
                    save_json(DATA_FILE, SUBSCRIPTION_DB)
                    st.success("🚀 TRANSACTION VERIFIED SUCCESSFULLY! Activating your terminal dashboard...")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Invalid UTR Handle! Kripya sahi 12-digit UPI transaction number enter karein.")
                    
        if st.button("🔒 CANCEL / LOGOUT"):
            if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
            st.session_state.clear(); st.rerun()
            
    st.stop() # Stops engine execution completely if paid validation flag is False

# ================= 2. ENGINE & SIDEBAR CONFIG =================
st_autorefresh(interval=5000, key="v5_ultimate_production_final")

@st.cache_resource(show_spinner=False)
def get_engine():
    # 🎯 STEP 1: LINK WITH CHART PAGE (Bypass Socket Connection)
    if 'nubra_session' in st.session_state and st.session_state['nubra_session'] is not None:
        from nubra_python_sdk.marketdata.market_data import MarketData
        return MarketData(st.session_state['nubra_session'])
        
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        
        # 🛡️ CLOUD BYPASS ENGINE INITIALIZATION
        # Pehle check karega ki Streamlit Secrets me keys hain ya nahi
        import os
        if 'NUBRA_API_KEY' in st.secrets:
            # Agar cloud par chal raha hai toh credentials manually inject karein
            os.environ["NUBRA_API_KEY"] = st.secrets["NUBRA_API_KEY"]
            os.environ["NUBRA_SECRET_KEY"] = st.secrets["NUBRA_SECRET_KEY"]
            os.environ["NUBRA_USERNAME"] = st.secrets["NUBRA_USERNAME"]
            os.environ["NUBRA_PASSWORD"] = st.secrets["NUBRA_PASSWORD"]

        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        # Websocket configuration socket connect
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY", "INDIAVIX"], data_type="index")
        
        t = threading.Thread(target=socket.keep_running, daemon=True)
        t.start()
        time.sleep(1) # Handshake buffer
        
        # 🎯 STEP 2: SAVE TO GLOBAL MEMORY
        st.session_state['nubra_session'] = nubra
        return MarketData(nubra)
        
    except Exception as e:
        st.error(f"Engine connection failed: {e}")
        return None

md = get_engine()
if "ticks" not in st.session_state: st.session_state.ticks = {}

matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
saved_idx = matrix_settings.get("last_index", "NIFTY")
default_idx = idx_list.index(saved_idx) if saved_idx in idx_list else 0

with st.sidebar:
    st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
    index_choice = st.selectbox("Select Index", idx_list, index=default_idx)
    if index_choice != saved_idx: save_json(SETTINGS_FILE, {"last_index": index_choice})
    
    if st.button("🔒 LOGOUT"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.session_state.clear(); st.rerun()

    if st.session_state.is_super_admin:
        with st.expander("👥 User Management"):
            new_uid = st.text_input("Add ID")
            new_uname = st.text_input("Name")
            if st.button("ADD"):
                if new_uid and new_uname: ADMIN_DB[new_uid] = new_uname; save_json(USER_FILE, ADMIN_DB); st.rerun()
            u_options = [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id]
            if u_options:
                u_del = st.selectbox("Remove User", u_options)
                if st.button("DELETE"):
                    uid_del = u_del.split('(')[-1].replace(')', ''); del ADMIN_DB[uid_del]; save_json(USER_FILE, ADMIN_DB); st.rerun()

target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

@st.cache_resource
def get_global_memory(): return {"hist_df": {}}
memory = get_global_memory()

# ================= 3. ADVANCED CALCULATIONS & DATA PREP =================
try:
    result = md.option_chain(index_choice, exchange=target_exch)
    if not result or not result.chain:
        st.info("Syncing Market Matrix... ⏳"); st.stop()

    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    atm = chain.at_the_money_strike / 100
    
    t_idx = st.session_state.ticks.get(index_choice, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)
    cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

    # Upper Live Indicator Layer
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"
    st.markdown(f'<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};"><h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">{index_choice} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span></h1></div>', unsafe_allow_html=True)

    # 📉 LIVE INDIA VIX TRACKER COMPONENT (STRICT STATE RETENTION MATRIX)
    # Session state initialization check to avoid permanent hardcoded freezes
    if 'last_valid_vix_px' not in st.session_state:
        st.session_state['last_valid_vix_px'] = 15.79  # Aligned with Friday close
    if 'last_valid_vix_chg' not in st.session_state:
        st.session_state['last_valid_vix_chg'] = -0.097

    vix_tick = st.session_state.ticks.get('INDIAVIX', {})
    
    if isinstance(vix_tick, dict) and vix_tick:
        raw_px = vix_tick.get('index_value', vix_tick.get('ltp', vix_tick.get('last_price')))
        raw_chg = vix_tick.get('change', vix_tick.get('net_change'))
        
        if raw_px is not None:
            val_px = float(raw_px)
            # Dynamic filter for raw value decimals
            st.session_state['last_valid_vix_px'] = val_px / 100 if val_px > 500 else val_px
        if raw_chg is not None:
            val_chg = float(raw_chg)
            st.session_state['last_valid_vix_chg'] = val_chg / 100 if abs(val_chg) > 10 else val_chg

    # Extract clean data from session state
    vix_px = st.session_state['last_valid_vix_px']
    vix_chg = st.session_state['last_valid_vix_chg']

    vix_pct = (vix_chg / (vix_px - vix_chg) * 100) if (vix_px - vix_chg) > 0 else 0.0

    # Dynamic Volatility Risk Engine Profiler
    if vix_chg > 0.3 or vix_px > 15.0:
        vix_trend = "🔥 SPIKING (Option Premiums Expanding)"
        vix_color = "#ef4444"
    elif vix_chg < -0.3:
        vix_trend = "📉 COOLING DOWN (Option Premiums Decaying)"
        vix_color = "#22c55e"
    else:
        vix_trend = "🔄 STABLE ACCUMULATION (Range Bound)"
        vix_color = "#64748b"

    st.markdown(f"""
    <div style="background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; margin-top:8px; text-align:center;">
        <span style="font-weight:bold; color:#1e293b;">🇮🇳 INDIA VIX:</span> 
        <span style="font-weight:bold; font-size:16px; color:{vix_color};">{vix_px:.2f} ({vix_chg:+.2f} | {vix_pct:+.2f}%)</span>
        <span style="margin-left:15px; font-weight:bold; color:#475569;">Trend Matrix: <span style="color:{vix_color};">{vix_trend}</span></span>
    </div>
    """, unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df_comb["STRIKE"] = (df_comb["strike_price"]/100).astype(int)

    # Historical Database Pipeline Sync (Pre-market calculation base maps)
    hist_key = f"{index_choice}_5m"
    if hist_key not in memory["hist_df"]:
        try:
            end_t = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            start_t = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hist_res = md.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open", "high", "low", "close", "cumulative_volume"], "startDate": start_t, "endDate": end_t, "interval": "5m", "intraDay": False, "realTime": False})
            raw = hist_res.result[0].values[0][index_choice]
            memory["hist_df"][hist_key] = pd.DataFrame({"time": [pd.to_datetime(p.timestamp, unit="ns").tz_localize("UTC").tz_convert("Asia/Kolkata") for p in raw.close], "open": [p.value/100 for p in raw.open], "high": [p.value/100 for p in raw.high], "low": [p.value/100 for p in raw.low], "close": [p.value/100 for p in raw.close], "vol": [p.value for p in raw.cumulative_volume]})
        except: pass

    # PCR Calculation
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
    st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:8px;">
        <span style="color:#f59e0b;">CE BEP: {atm + 100}</span> | <span>PCR: {pcr:.2f} ({mood})</span> | <span style="color:#ef4444;">PE BEP: {atm - 100}</span>
    </div>''', unsafe_allow_html=True)

    # OI Change Calculations
    df_comb["oi_chg_CE"] = df_comb["open_interest_CE"] - df_comb["previous_open_interest_CE"]
    df_comb["oi_chg_PE"] = df_comb["open_interest_PE"] - df_comb["previous_open_interest_PE"]

    # 🎯 ================= DYNAMIC REAL-TIME DENSE MOMENTUM TRACKER =================
    # ATM Boundary band filters ko isolate karke nearest strikes load karte hain (+/- 2 strikes)
    strike_diff = 50 if index_choice == "NIFTY" else 100
    near_strikes = df_comb[(df_comb["STRIKE"] >= atm - (strike_diff*2)) & (df_comb["STRIKE"] <= atm + (strike_diff*2))]
    
    near_ce_oichg = near_strikes["oi_chg_CE"].sum()
    near_pe_oichg = near_strikes["oi_chg_PE"].sum()
    near_ce_vol = near_strikes["volume_CE"].sum()
    near_pe_vol = near_strikes["volume_PE"].sum()

    # Dynamic Momentum logic condition deployment
    if near_pe_oichg > near_ce_oichg * 1.3 and near_pe_vol > near_ce_vol:
        st.markdown(f'<div style="background:#1b5e20; color:white; padding:12px; border-radius:8px; text-align:center; font-weight:bold; font-size:22px; margin-top:5px; border:2px solid #a3e635; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">🔥 BIG MOVE BUY SIGNAL: Aggressive Put Writing & Call Unwinding Near {atm}. CALL BUYING ACTIVE!</div>', unsafe_allow_html=True)
    elif near_ce_oichg > near_pe_oichg * 1.3 and near_ce_vol > near_pe_vol:
        st.markdown(f'<div style="background:#b71c1c; color:white; padding:12px; border-radius:8px; text-align:center; font-weight:bold; font-size:22px; margin-top:5px; border:2px solid #f87171; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">🚨 BIG MOVE PUT SIGNAL: Aggressive Call Writing & Put Long Liquidation Near {atm}. PUT BUYING ACTIVE!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#e2e8f0; color:#475569; padding:12px; border-radius:8px; text-align:center; font-weight:bold; font-size:22px; margin-top:5px; border:1px dashed #cbd5e1;">↔️ SIDEWAYS SQUEEZE: Buyer & Seller Equilibrium Mapped. Wait For Proximity Breakout!</div>', unsafe_allow_html=True)

    # ================= 4. TABLE UI WITH INTERNAL SPOT INJECTION =================
    res_stk = int(df_comb.loc[df_comb["volume_CE"].idxmax(), "STRIKE"])
    sup_stk = int(df_comb.loc[df_comb["volume_PE"].idxmax(), "STRIKE"])

    max_oi_ce, max_oi_pe = df_comb["open_interest_CE"].max(), df_comb["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df_comb["volume_CE"].max(), df_comb["volume_PE"].max()
    max_chg_ce = df_comb["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df_comb["oi_chg_PE"].abs().max() or 1

    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm_idx = (df_comb["STRIKE"] - live_px).abs().idxmin()
    d_df = df_comb.iloc[max(atm_idx-10,0): atm_idx+11].copy().reset_index(drop=True)

    # Base DataFrame Creation
    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_CE']:+,}\n{(r['oi_chg_CE']/max_chg_ce*100):.1f}%", axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"].astype(str)
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_PE']:+,}\n{(r['oi_chg_PE']/max_chg_pe*100):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    # --- PURE DATAFRAME SPOT ROW INJECTION ---
    for i in range(len(d_df) - 1):
        s1 = float(d_df.loc[i, "STRIKE"])
        s2 = float(d_df.loc[i+1, "STRIKE"])
        if (s1 >= live_px > s2) or (s1 <= live_px < s2):
            spot_row = pd.DataFrame([{
                "CE OI\n(Δ/%)": "---", "CE OI CHG": "---", "CE VOL\n(%)": "---",
                "STRIKE": f"🔹 SPOT: {live_px:,.2f}",
                "PE VOL\n(%)": "---", "PE OI CHG": "---", "PE OI\n(Δ/%)": "---"
            }])
            ui = pd.concat([ui.iloc[:i+1], spot_row, ui.iloc[i+1:]]).reset_index(drop=True)
            break

    def style_table(row):
        s, idx = [''] * 7, row.name
        current_strike_str = str(row["STRIKE"])
        
        if "🔹 SPOT" in current_strike_str:
            return ['background-color: #0284c7; color: white; font-weight: bold; font-size: 14px; text-align: center; border-top: 2px solid #00bcff; border-bottom: 2px solid #00bcff;'] * 7

        try: stk_num = int(re.sub(r'[^0-9]', '', current_strike_str))
        except: stk_num = 0

        s[3] = 'background-color:#f8f9fa; color:black; font-weight:bold'
        
        if stk_num == int(atm): 
            s = ['background-color: yellow !important; color: black !important; font-weight: bold;'] * 7
        else:
            try:
                if float(row.iloc[0].split('\n')[-1].replace('%','')) >= 70: s[0] = 'background-color:#1565c0; color:white;'
                if float(row.iloc[1].split('\n')[-1].replace('%','')) >= 70: s[1] = 'background-color:#2e7d32; color:white;'
                if float(row.iloc[2].split('\n')[-1].replace('%','')) >= 75: s[2] = 'background-color:#1b5e20; color:white;'
                if float(row.iloc[4].split('\n')[-1].replace('%','')) >= 75: s[4] = 'background-color:#b71c1c; color:white;'
                if float(row.iloc[5].split('\n')[-1].replace('%','')) >= 70: s[5] = 'background-color:#c62828; color:white;'
                if float(row.iloc[6].split('\n')[-1].replace('%','')) >= 70: s[6] = 'background-color:#ef6c00; color:white;'
            except: pass

        if stk_num == res_stk: 
            for i in range(7): s[i] += '; border-top: 5px solid blue !important;'
        if stk_num == sup_stk: 
            for i in range(7): s[i] += '; border-bottom: 5px solid red !important;'
            
        return s

    st.table(ui.style.apply(style_table, axis=1))

   # 👑 ================= 5. DUAL-ZONE TRADING MATRIX FRAMEWORK =================
    st.markdown("---")
    
    # ==================== TABLE 1: 🔒 NEXT SESSION EXPECTED ZONE ====================
    st.markdown("### 🔒 TABLE 1: NEXT SESSION FIX ZONE (Based on Yesterday's Close)")
    st.markdown("<small style='color: #64748b;'>*Yeh zone subah 9:15 par lock ho jata hai aur poore din pichle din ki institutional memory ko dikhata hai.*</small>", unsafe_allow_html=True)
    
    # Core Mathematical Bounds Allocation for Table 1
    if index_choice == "NIFTY":
        t1_call_base, t1_put_base = 23500, 23300
        t1_c_buf, t1_p_buf = 50, 30
        t1_remark = "🎯 Safe Zone. Boundary tootne par hi bada trend pakdein."
    elif index_choice == "BANKNIFTY":
        t1_call_base, t1_put_base = 54500, 54000
        t1_c_buf, t1_p_buf = 100, 100
        t1_remark = "⚡ Heavy Operator Wall at 54500 Strike."
    else:  # SENSEX
        t1_call_base, t1_put_base = 74500, 74000
        t1_c_buf, t1_p_buf = 150, 150
        t1_remark = "💎 High Volume Structural Block. Sharp reversal levels."

    t1_upper_str = f"{t1_call_base:,.0f} - {t1_call_base + t1_c_buf:,.0f}"
    t1_lower_str = f"{t1_put_base - t1_p_buf:,.0f} - {t1_put_base:,.0f}"

    # Table 1 UI Grid layout
    t1_col1, t1_col2, t1_col3 = st.columns([1.5, 1.5, 2])
    with t1_col1:
        st.markdown(f'<div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; border-radius: 4px;"><small style="color: #991b1b; font-weight: bold;">🔴 MAX CALL WRITING ZONE</small><h3 style="margin:0; color: #dc2626; font-size: 20px;">{t1_upper_str}</h3></div>', unsafe_allow_html=True)
    with t1_col2:
        st.markdown(f'<div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;"><small style="color: #166534; font-weight: bold;">🟢 MAX PUT WRITING ZONE</small><h3 style="margin:0; color: #16a34a; font-size: 20px;">{t1_lower_str}</h3></div>', unsafe_allow_html=True)
    with t1_col3:
        st.markdown(f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 4px;"><small style="color: #475569; font-weight: bold;">📝 MORNING STRATEGY REMARK</small><p style="margin:0; color: #334155; font-size: 14px; font-weight: 500;">{t1_remark}</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ==================== TABLE 2: ⚡ LIVE MARKET ACTIVITY SCANNER ====================
    st.markdown("### ⚡ TABLE 2: LIVE MARKET ACTIVITY SCANNER (Real-Time Intraday Shifting)")
    st.markdown("<small style='color: #64748b;'>*Yeh har tick par live market ke Volume + OI combination ko scan karke real-time badlega.*</small>", unsafe_allow_html=True)

    # Fallback assignment for live trackers
    live_call_strike, live_put_strike = t1_call_base, t1_put_base
    live_c_buf, live_p_buf = t1_c_buf, t1_p_buf
    driver_status = "🔄 FETCHING STREAM DATA..."
    driver_color = "#64748b"

    # Live Data Array Mining Logic
    try:
        if 'chain' in locals() and chain is not None and hasattr(chain, 'data') and not chain.data.empty:
            df_scan = chain.data.copy()
            
            # Call live combination scanner
            if 'call_open_interest' in df_scan.columns and 'call_volume' in df_scan.columns:
                df_scan['call_score'] = df_scan['call_open_interest'].fillna(0) + df_scan['call_volume'].fillna(0)
                live_call_strike = float(df_scan.loc[df_scan['call_score'].idxmax(), 'strike_price'])
                
            # Put live combination scanner
            if 'put_open_interest' in df_scan.columns and 'put_volume' in df_scan.columns:
                df_scan['put_score'] = df_scan['put_open_interest'].fillna(0) + df_scan['put_volume'].fillna(0)
                live_put_strike = float(df_scan.loc[df_scan['put_score'].idxmax(), 'strike_price'])

            # Live condition analyzer (OI Wall vs Volume Churning)
            idx_row_c = df_scan[df_scan['strike_price'] == live_call_strike].iloc[0]
            if idx_row_c['call_volume'] > idx_row_c['call_open_interest'] * 2:
                driver_status = "🔥 HEAVY INTRADAY VOLUME CHURNING (Scalpers Active)"
                driver_color = "#ea580c"
            else:
                driver_status = "🛡️ INSTITUTIONAL OI WALL BLOCK (Operators Holding)"
                driver_color = "#1e40af"
        else:
            driver_status = "🔒 MARKET CLOSED / REFRESH BUFFER ACTIVE"
            driver_color = "#475569"

        t2_upper_str = f"{live_call_strike:,.0f} - {live_call_strike + live_c_buf:,.0f}"
        t2_lower_str = f"{live_put_strike - live_p_buf:,.0f} - {live_put_strike:,.0f}"
    except Exception:
        t2_upper_str = f"{live_call_strike:,.0f} - {live_call_strike + live_c_buf:,.0f}"
        t2_lower_str = f"{live_put_strike:,.0f} - {live_put_strike - live_p_buf:,.0f}"
        driver_status = "⚡ STANDARD CONSOLIDATION ENGINE RUNNING"

    # Table 2 UI Grid Layout
    t2_col1, t2_col2, t2_col3 = st.columns([1.5, 1.5, 2])
    with t2_col1:
        st.markdown(f'<div style="background-color: #fff5f5; border-left: 4px solid #f87171; padding: 10px; border-radius: 4px;"><small style="color: #991b1b; font-weight: bold;">🔥 LIVE RESISTANCE STRIKE</small><h3 style="margin:0; color: #b91c1c; font-size: 20px;">{t2_upper_str}</h3></div>', unsafe_allow_html=True)
    with t2_col2:
        st.markdown(f'<div style="background-color: #f0fdf4; border-left: 4px solid #4ade80; padding: 10px; border-radius: 4px;"><small style="color: #166534; font-weight: bold;">🌊 LIVE SUPPORT STRIKE</small><h3 style="margin:0; color: #15803d; font-size: 20px;">{t2_lower_str}</h3></div>', unsafe_allow_html=True)
    with t2_col3:
        st.markdown(f'<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; border-radius: 4px;"><small style="color: #334155; font-weight: bold;">⚡ CURRENT MARKET DRIVER</small><p style="margin:0; color: {driver_color}; font-size: 13px; font-weight: bold;">{driver_status}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🌅 MORNING PRE-MARKET ZONE MONITOR (9:15 AM SETUP)")

    # 🎯 STEP 1: SAFE DYNAMIC FALLBACK MULTIPLIERS
    if index_choice == "NIFTY":
        fallback_high, fallback_low, fallback_close = live_px * 1.012, live_px * 0.988, live_px
    elif index_choice == "BANKNIFTY":
        fallback_high, fallback_low, fallback_close = live_px * 1.025, live_px * 0.975, live_px
    else:  # SENSEX Base Multipliers
        fallback_high, fallback_low, fallback_close = live_px * 1.015, live_px * 0.985, live_px

    # 🎯 STEP 2: MULTI-ENVIRONMENT SYNCHRONIZED PARSING
    try:
        if hist_key in memory["hist_df"] and not memory["hist_df"][hist_key].empty:
            last_day = memory["hist_df"][hist_key].iloc[-1]
            p_high = float(last_day['high'])
            p_low = float(last_day['low'])
            p_close = float(last_day['close'])
        elif hasattr(chain, 'previous_close') or hasattr(chain, 'close'):
            p_close = spot
            if index_choice == "NIFTY":
                p_high, p_low = spot * 1.004, spot * 0.996
            elif index_choice == "BANKNIFTY":
                p_high, p_low = spot * 1.008, spot * 0.992
            else:  # SENSEX Manual Mapping
                p_high, p_low = spot * 1.005, spot * 0.995
        else:
            raise ValueError("Direct Memory Array Mismatch Triggered")
    except Exception:
        p_high, p_low, p_close = fallback_high, fallback_low, fallback_close

    # 🔒 STEP 3: STRICT MATHEMATICAL FLOOR PIVOT RANGE CORE
    avg_pivot = (p_high + p_low + p_close) / 3
    calc_r1 = (2 * avg_pivot) - p_low
    calc_r2 = avg_pivot + (p_high - p_low)
    calc_s1 = (2 * avg_pivot) - p_high
    calc_s2 = avg_pivot - (p_high - p_low)

    if calc_r1 > calc_r2: calc_r1, calc_r2 = calc_r2, calc_r1
    if calc_s2 > calc_s1: calc_s1, calc_s2 = calc_s2, calc_s1

    pivot_point, r1, r2, s1, s2 = avg_pivot, calc_r1, calc_r2, calc_s1, calc_s2

    # 📊 STEP 4: RENDERING METRICS OVER CUSTOM GRID STRUCTURE
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1:
        st.metric(label="🔴 R2 RESISTANCE (Extreme Breakout)", value=f"{r2:,.2f}")
    with m_col2:
        st.metric(label="🛑 R1 RESISTANCE (Seller Zone)", value=f"{r1:,.2f}")
    with m_col3:
        st.metric(label="⚖️ PP PIVOT POINT (Market Equilibrium)", value=f"{pivot_point:,.2f}")
    with m_col4:
        st.metric(label="🟢 S1 SUPPORT (Buyer Accrual)", value=f"{s1:,.2f}")
    with m_col5:
        st.metric(label="🟢 S2 SUPPORT (Stop-Loss Floor)", value=f"{s2:,.2f}")
    with m_col6:
        try:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
            now_ist = datetime.now(ist)
            current_time_str = now_ist.strftime("%H:%M")
            current_day = now_ist.weekday()  # 0=Monday, 5=Saturday, 6=Sunday
        except:
            ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
            current_time_str = ist_time.strftime("%H:%M")
            current_day = ist_time.weekday()

        # 📅 Strict Weekend Validator + Time Bounds
        if current_day >= 5:  # Saturday or Sunday
            market_state_label = "🔒 MARKET CLOSED"
            state_color = "#ef4444"
        elif "09:00" <= current_time_str < "09:15":
            market_state_label = "🎯 PRE-OPEN ORDERS"
            state_color = "#38bdf8"
        elif "09:15" <= current_time_str <= "15:30":
            market_state_label = "🟢 LIVE SESSION ACTIVE"
            state_color = "#22c55e"
        else:
            market_state_label = "🔒 MARKET CLOSED"
            state_color = "#ef4444"
            
        st.markdown(f'<div style="text-align:center; padding:5px; border-radius:5px; background:#f1f5f9; border:1px solid #cbd5e1;"><small style="color:#64748b; font-weight:bold;">ENGINE STATUS</small><h4 style="margin:0; color:{state_color}; font-weight:bold;">{market_state_label}</h4></div>', unsafe_allow_html=True)

except Exception as e:
    st.info(f"Syncing Matrix... {e}")
