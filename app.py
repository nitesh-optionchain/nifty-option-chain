from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# Session state for Authentication
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.admin_name = "Guest"

# ================= 2. FILE STORAGE =================
DATA_FILE = "admin_data.json"
USER_FILE = "authorized_users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
        "sr": {"support": "-", "resistance": "-"}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

def load_users():
    default_admins = {"9304768496": "Admin Chief", "9822334455": "Amit Kumar", "9011223344": "Amit Sharma"}
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f: return json.load(f)
    return default_admins

def save_users(users):
    with open(USER_FILE, "w") as f: json.dump(users, f)

data = load_data()
ADMIN_DB = load_users()

# ================= 3. LOGIN FIREWALL (CRITICAL) =================

# 1. URL ID Check
query_params = st.query_params
url_id = query_params.get("id", None)

if url_id in ADMIN_DB:
    st.session_state.auth = True
    st.session_state.admin_name = ADMIN_DB[url_id]

# 2. Login Screen (Agar authenticated nahi hai toh)
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Please Login to Access Dashboard</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("Login Form"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            submit = st.form_submit_button("LOGIN")
            if submit:
                if user_key in ADMIN_DB:
                    st.session_state.auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.rerun()
                else:
                    st.error("Invalid ID. Access Denied.")
    
    st.stop() # Dashboard ko load hone se rokh dega

# ================= 4. DASHBOARD (SIRF LOGIN KE BAAD) =================
st_autorefresh(interval=5000, key="refresh")
is_admin = True # Yahan tak wahi pahunchega jo authenticated hai
current_admin_name = st.session_state.admin_name

st.sidebar.success(f"⚡ Logged in as: {current_admin_name}")

# Add User Option (Sidebar)
with st.sidebar.expander("👤 Admin: Add New User"):
    new_name = st.text_input("User Name")
    new_mobile = st.text_input("User Mobile")
    if st.button("Register"):
        if new_mobile and new_name:
            ADMIN_DB[new_mobile] = new_name
            save_users(ADMIN_DB)
            st.sidebar.success(f"Added: {new_name}")

# Ticker
ticker_html = """<div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-tickers.js" async>{"symbols": [{"proName": "NSE:NIFTY", "title": "NIFTY 50"},{"proName": "NSE:BANKNIFTY", "title": "BANK NIFTY"},{"proName": "NSE:INDIAVIX", "title": "INDIA VIX"}],"colorTheme": "dark","isTransparent": true,"locale": "en"}</script></div>"""
components.html(ticker_html, height=80)

# SDK & Data
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")
if not result: st.stop()
chain = result.chain

# Header
try:
    spot = chain.ce[0].underlying_price / 100
except:
    spot = chain.at_the_money_strike / 100

st.title("🛡️ SMART WEALTH AI 5")
st.subheader(f"📊 LIVE NIFTY: {spot:,.2f}")

# Dataframes
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Change Track
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

# Signals & SR (Admin Section)
st.subheader("🎯 LIVE TRADE SIGNALS")
c1, c2, c3, c4, c5 = st.columns(5)
s_strike = c1.text_input("Strike", value=data["signal"]["Strike"])
s_entry = c2.text_input("Entry", value=data["signal"]["Entry"])
s_target = c3.text_input("Target", value=data["signal"]["Target"])
s_sl = c4.text_input("SL", value=data["signal"]["SL"])
if c5.button("📢 UPDATE"):
    data["signal"] = {"Strike": s_strike, "Entry": s_entry, "Target": s_target, "SL": s_sl, "Status": f"LIVE ({current_admin_name})"}
    save_data(data)
    st.rerun()

st.subheader("📊 SUPPORT / RESISTANCE")
sr_1, sr_2, sr_3 = st.columns(3)
sup = sr_1.text_input("Support", data["sr"]["support"])
res = sr_2.text_input("Resistance", data["sr"]["resistance"])
if sr_3.button("SET"):
    data["sr"] = {"support": sup, "resistance": res}
    save_data(data)
    st.rerun()

# Table UI & Formatting (As per original)
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

def final_style(row):
    styles = [''] * len(row)
    try:
        ce_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
        ce_vol = float(row.iloc[2].split('\n')[-1].replace('%',''))
        pe_vol = float(row.iloc[4].split('\n')[-1].replace('%',''))
        pe_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))
        if ce_oi > 65: styles[1] = 'background-color:#0d47a1;color:white'
        if ce_vol >= 90: styles[2] = 'background-color:#00c853;color:white'
        if pe_oi > 65: styles[5] = 'background-color:#ff6f00;color:white'
        if pe_vol >= 90: styles[4] = 'background-color:#d50000;color:white'
        if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
        else: styles[3] = 'background-color:#eeeeee'
    except: pass
    return styles

st.table(ui.style.apply(final_style, axis=1))
