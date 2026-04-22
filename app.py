from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ================= 2. USER & DATA STORAGE (ERROR FIX) =================
USER_FILE = "authorized_users.json"
DATA_FILE = "admin_data.json"

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                content = json.load(f)
                return content if content else default
        except: return default
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# --- ADMIN LIST ---
ADMIN_NUMBERS = ["9304768496", "98XXXXXXXX", "99XXXXXXXX"] 

# Data Loading with Force-Repair Logic
auth_users = load_json(USER_FILE, {num: "Admin" for num in ADMIN_NUMBERS})
raw_data = load_json(DATA_FILE, {})

# Agar keys missing hain toh Error nahi aayega, default value load hogi
data = {
    "signal": raw_data.get("signal", {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}),
    "sr": raw_data.get("sr", {"s1": "-", "s2": "-", "r1": "-", "r2": "-"})
}

# ================= 3. LOGIN SCREEN =================
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.form("Login"):
            mobile = st.text_input("Mobile Number", type="password")
            if st.form_submit_button("LOGIN"):
                if mobile in auth_users:
                    st.session_state.authenticated = True
                    st.session_state.mobile = mobile
                    st.session_state.user_name = auth_users[mobile]
                    st.rerun()
                else: st.error("Access Denied")
    st.stop()

# ================= 4. DASHBOARD LOGIC =================
st_autorefresh(interval=5000, key="refresh")
is_admin = (st.session_state.mobile in ADMIN_NUMBERS)

# Admin Sidebar
if is_admin:
    with st.sidebar.expander("👤 Admin Control"):
        u_n = st.text_input("New User Name")
        u_m = st.text_input("New User Mobile")
        if st.button("Register User"):
            auth_users[u_m] = u_n
            save_json(USER_FILE, auth_users)
            st.success("Authorized!")

# Ticker Widget
ticker_html = """<div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-tickers.js" async>{"symbols": [{"proName": "NSE:NIFTY", "title": "NIFTY 50"},{"proName": "NSE:BANKNIFTY", "title": "BANK NIFTY"},{"proName": "NSE:INDIAVIX", "title": "INDIA VIX"}],"colorTheme": "dark","isTransparent": true,"locale": "en"}</script></div>"""
components.html(ticker_html, height=80)

# SDK Fetch
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")
if not result: st.stop()
chain = result.chain

# Header Metrics
try:
    spot = chain.ce[0].underlying_price / 100
    atm_val = int(round(spot / 50) * 50)
    change_pts = spot - 24500 # Example prev close
except: spot, atm_val, change_pts = 0.0, 0, 0.0

st.title("🛡️ SMART WEALTH AI 5")
h1, h2, h3 = st.columns(3)
h1.metric("📊 NIFTY LIVE", f"{spot:,.2f}", f"{change_pts:+.2f}")
h2.metric("🎯 ATM STRIKE", f"{atm_val}")
h3.metric("📉 INDIA VIX", "13.45")
st.markdown("---")

# ================= 5. S/R TABLE (ADMIN UPDATABLE) =================
st.subheader("📉 Support & Resistance")
sr_cols = st.columns(5)

if is_admin:
    r2_val = sr_cols[0].text_input("R2", value=data["sr"]["r2"])
    r1_val = sr_cols[1].text_input("R1", value=data["sr"]["r1"])
    s1_val = sr_cols[2].text_input("S1", value=data["sr"]["s1"])
    s2_val = sr_cols[3].text_input("S2", value=data["sr"]["s2"])
    if sr_cols[4].button("Update S/R"):
        data["sr"] = {"s1": s1_val, "s2": s2_val, "r1": r1_val, "r2": r2_val}
        save_json(DATA_FILE, data)
        st.rerun()
else:
    sr_cols[0].error(f"R2: {data['sr']['r2']}")
    sr_cols[1].error(f"R1: {data['sr']['r1']}")
    sr_cols[2].success(f"S1: {data['sr']['s1']}")
    sr_cols[3].success(f"S2: {data['sr']['s2']}")

st.markdown("---")

# ================= 6. LIVE SIGNALS =================
st.subheader("🎯 Trade Signals")
sig_cols = st.columns(5)
if is_admin:
    s_st = sig_cols[0].text_input("Strike", value=data["signal"]["Strike"])
    s_en = sig_cols[1].text_input("Entry", value=data["signal"]["Entry"])
    s_tg = sig_cols[2].text_input("Target", value=data["signal"]["Target"])
    s_sl = sig_cols[3].text_input("SL", value=data["signal"]["SL"])
    if sig_cols[4].button("Update Signal"):
        data["signal"] = {"Strike": s_st, "Entry": s_en, "Target": s_tg, "SL": s_sl, "Status": "LIVE"}
        save_json(DATA_FILE, data)
        st.rerun()
else:
    sig_cols[0].info(f"STRIKE: {data['signal']['Strike']}")
    sig_cols[1].success(f"ENTRY: {data['signal']['Entry']}")
    sig_cols[2].warning(f"TARGET: {data['signal']['Target']}")
    sig_cols[3].error(f"SL: {data['signal']['SL']}")
    sig_cols[4].write(f"Status: {data['signal']['Status']}")

# ================= 7. OPTION CHAIN (ORIGINAL STYLE) =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Buildup logic
if "prev_df" not in st.session_state: st.session_state.prev_df = None
if st.session_state.prev_df is not None:
    prev = st.session_state.prev_df.set_index("STRIKE")
    curr = df.set_index("STRIKE")
    df["oi_chg_CE"] = df["STRIKE"].map(curr["open_interest_CE"] - prev["open_interest_CE"]).fillna(0)
    df["oi_chg_PE"] = df["STRIKE"].map(curr["open_interest_PE"] - prev["open_interest_PE"]).fillna(0)
    df["prc_chg_CE"] = df["STRIKE"].map(curr["last_traded_price_CE"] - prev["last_traded_price_CE"]).fillna(0)
    df["prc_chg_PE"] = df["STRIKE"].map(curr["last_traded_price_PE"] - prev["last_traded_price_PE"]).fillna(0)
else:
    df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0
st.session_state.prev_df = df.copy()

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm_idx = df.index[df["STRIKE"] >= int(spot)][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
ui["CE OI"] = display_df.apply(lambda r: f"{r['open_interest_CE']:,.0f}\n({r['oi_chg_CE']:+,})\n{(r['open_interest_CE']/df['open_interest_CE'].max()*100):.1f}%", axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE OI"] = display_df.apply(lambda r: f"{r['open_interest_PE']:,.0f}\n({r['oi_chg_PE']:+,})\n{(r['open_interest_PE']/df['open_interest_PE'].max()*100):.1f}%", axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

def apply_color(row):
    styles = [''] * len(row)
    try:
        c_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
        p_oi = float(row.iloc[3].split('\n')[-1].replace('%',''))
        if c_oi > 65: styles[1] = 'background-color:#0d47a1;color:white'
        if p_oi > 65: styles[3] = 'background-color:#ff6f00;color:white'
        if row["STRIKE"] == atm_val: styles[2] = 'background-color:yellow;color:black'
    except: pass
    return styles

st.subheader("📊 Institutional Data")
st.table(ui.style.apply(apply_color, axis=1))
