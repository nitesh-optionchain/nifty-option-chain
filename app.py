from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.admin_name = "Guest"

# ================= 2. FILE STORAGE (SAFE PATHS) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "admin_data.json")
USER_FILE = os.path.join(BASE_DIR, "authorized_users.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: pass
    return {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
        "sr": {"support": "-", "resistance": "-"}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

def load_users():
    default_admins = {"9304768496": "Admin Chief", "9822334455": "Amit Kumar"}
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f: return json.load(f)
        except: pass
    return default_admins

def save_users(users):
    with open(USER_FILE, "w") as f: json.dump(users, f)

data = load_data()
ADMIN_DB = load_users()

# ================= 3. LOGIN FIREWALL (STRICT) =================
query_params = st.query_params
url_id = query_params.get("id", None)

if url_id and url_id in ADMIN_DB and not st.session_state.auth:
    st.session_state.auth = True
    st.session_state.admin_name = ADMIN_DB[url_id]

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #00ff00;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("Login_Form"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Access Denied!")
    st.stop()

# ================= 4. TICKER HEADER (TICKER TAPE) =================
st_autorefresh(interval=5000, key="refresh")

# Investing.com Ticker Tape (Simplified)
ticker_html = """
<div style="width: 100%; background-color: #000; border-bottom: 2px solid #333;">
    <iframe src="https://www.widgets.investing.com/live-indices-ticker?theme=darkTheme&pairs=179,953086,172,166" 
    width="100%" height="40" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0" scrolling="no"></iframe>
</div>
"""
components.html(ticker_html, height=50)

# Sidebar Admin Control
with st.sidebar.expander("👤 User Management"):
    u_n = st.text_input("Name")
    u_m = st.text_input("Mobile")
    if st.button("Register"):
        if u_m and u_n:
            ADMIN_DB[u_m] = u_n
            save_users(ADMIN_DB)
            st.sidebar.success("User Added")

# ================= 5. DATA FETCH (SDK) =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")

if not result:
    st.warning("🔄 Waiting for Live Data from SDK...")
    st.stop()

chain = result.chain
try:
    spot = chain.ce[0].underlying_price / 100
except:
    spot = chain.at_the_money_strike / 100

st.title(f"🛡️ SMART WEALTH AI 5 | NIFTY: {spot:,.2f}")

# ================= 6. LIVE SIGNALS & S/R =================
st.markdown("---")
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("🎯 TRADE SIGNALS")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    s_st = sc1.text_input("Strike", value=data["signal"]["Strike"])
    s_en = sc2.text_input("Entry", value=data["signal"]["Entry"])
    s_tg = sc3.text_input("Target", value=data["signal"]["Target"])
    s_sl = sc4.text_input("SL", value=data["signal"]["SL"])
    if sc5.button("📢 UPDATE"):
        data["signal"] = {"Strike": s_st, "Entry": s_en, "Target": s_tg, "SL": s_sl, "Status": "LIVE"}
        save_data(data)
        st.rerun()

with col_b:
    st.subheader("📊 S/R LEVELS")
    sr1, sr2, sr3 = st.columns(3)
    s_v = sr1.text_input("Sup", data["sr"]["support"])
    r_v = sr2.text_input("Res", data["sr"]["resistance"])
    if sr3.button("📝 SET"):
        data["sr"] = {"support": s_v, "resistance": r_v}
        save_data(data)
        st.rerun()

# Metrics Display
m1, m2, m3, m4 = st.columns(4)
m1.metric("🟢 SUPPORT", data["sr"]["support"])
m2.metric("🔴 RESISTANCE", data["sr"]["resistance"])
m3.metric("🎯 ENTRY", data["signal"]["Entry"])
m4.metric("📊 STATUS", data["signal"]["Status"])

# ================= 7. OPTION CHAIN TABLE =================
st.markdown("---")
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Delta Calculations
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

def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-8,0): atm_idx+9].copy()

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
        pe_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))
        if ce_oi > 65: styles[1] = 'background-color:#0d47a1;color:white'
        if pe_oi > 65: styles[5] = 'background-color:#ff6f00;color:white'
        if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
        else: styles[3] = 'background-color:#eeeeee'
    except: pass
    return styles

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(final_style, axis=1))

st.sidebar.info(f"⚡ Logged in as: {st.session_state.admin_name}")
