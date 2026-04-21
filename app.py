from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# ================= FILE STORAGE =================
DATA_FILE = "admin_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
        "sr": {"support": "-", "resistance": "-"}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ================= ADMIN DB =================
ADMIN_DB = {
    "9304768496": "Admin Chief",
    "9822334455": "Amit Kumar",
    "9011223344": "Amit Sharma"
}

# ================= FIXED AUTH SYSTEM =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def login_page():
    st.title("🔐 ADMIN LOGIN")

    u = st.text_input("User ID")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in ADMIN_DB and p == u:   # simple secure admin check
            st.session_state.logged_in = True
            st.session_state.user = u
            st.success("Admin Login Success")
            st.rerun()
        else:
            st.error("Access Denied")

# 🔥 BLOCK APP UNTIL LOGIN
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ================= ADMIN STATUS =================
is_admin = True
current_admin_name = ADMIN_DB.get(st.session_state.user, "Guest")

st.sidebar.success(f"⚡ {current_admin_name}")

# ================= LOGOUT =================
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

# ================= SDK =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

nubra = st.session_state.nubra
market_data = MarketData(nubra)

# ================= DATA =================
result = market_data.option_chain("NIFTY", exchange="NSE")
if not result:
    st.stop()

chain = result.chain

# ================= LIVE NIFTY =================
try:
    spot = chain.ce[0].underlying_price / 100
except:
    spot = chain.at_the_money_strike / 100

st.title("🛡️ SMART WEALTH AI 5")
st.subheader(f"📊 LIVE NIFTY: {spot:,.2f}")

# ================= TRADINGVIEW =================
chart_url = "https://www.tradingview.com/chart/?symbol=NSE:NIFTY"

st.markdown(
    f"""
    <a href="{chart_url}" target="_blank">
        <button style="
            width:100%;
            background:#2962ff;
            color:white;
            padding:10px;
            border:none;
            border-radius:6px;
        ">
        📈 Open TradingView Chart
        </button>
    </a>
    """,
    unsafe_allow_html=True
)

# ================= DATAFRAME =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ================= CHANGE TRACK =================
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

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

# ================= ADMIN SIGNAL =================
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

s_strike = c1.text_input("Strike", data["signal"]["Strike"])
s_entry = c2.text_input("Entry", data["signal"]["Entry"])
s_target = c3.text_input("Target", data["signal"]["Target"])
s_sl = c4.text_input("SL", data["signal"]["SL"])

if c5.button("📢 UPDATE"):
    data["signal"] = {
        "Strike": s_strike,
        "Entry": s_entry,
        "Target": s_target,
        "SL": s_sl,
        "Status": f"LIVE ({current_admin_name})"
    }
    save_data(data)
    st.success("Signal Updated")

# ================= SUPPORT / RESISTANCE =================
st.subheader("📊 SUPPORT / RESISTANCE")

s1, s2, s3 = st.columns(3)

sup = s1.text_input("Support", data["sr"]["support"])
res = s2.text_input("Resistance", data["sr"]["resistance"])

if s3.button("SET"):
    data["sr"] = {"support": sup, "resistance": res}
    save_data(data)

a, b = st.columns(2)
a.metric("🟢 SUPPORT", data["sr"]["support"])
b.metric("🔴 RESISTANCE", data["sr"]["resistance"])

# ================= OPTION CHAIN (UNCHANGED) =================
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

st.table(ui)
