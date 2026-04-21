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

# ================= ADMIN =================
ADMIN_DB = {
    "9304768496": "Admin Chief", 
    "9822334455": "Amit Kumar",
    "9011223344": "Amit Sharma"
}

query_params = st.query_params
url_id = query_params.get("id", None)

is_admin = False
current_admin_name = "Guest"

if url_id in ADMIN_DB:
    is_admin = True
    current_admin_name = ADMIN_DB[url_id]
    st.sidebar.success(f"⚡ {current_admin_name}")
else:
    with st.sidebar.expander("🔑 Admin Login"):
        user_key = st.text_input("Enter Mobile ID:", type="password")
        if user_key in ADMIN_DB:
            is_admin = True
            current_admin_name = ADMIN_DB[user_key]
            st.sidebar.success(f"✅ {current_admin_name}")

# ================= 👤 USER CREATE SYSTEM (NEW ADDITION ONLY) =================
if "users" not in st.session_state:
    st.session_state.users = ADMIN_DB.copy()

st.sidebar.subheader("👤 User Management")

if is_admin:
    new_id = st.sidebar.text_input("New User ID")
    new_name = st.sidebar.text_input("New User Name")

    if st.sidebar.button("➕ Create User"):
        if new_id and new_name:
            st.session_state.users[new_id] = new_name
            st.sidebar.success(f"User Created: {new_name}")
        else:
            st.sidebar.error("Fill all fields")

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

# ================= 📈 TRADINGVIEW CHART (ADDED ONLY) =================
st.markdown(
    """
    <a href="https://www.tradingview.com/chart/?symbol=NSE:NIFTY" target="_blank">
        <button style="
            width:100%;
            background:#2962ff;
            color:white;
            padding:10px;
            border:none;
            border-radius:6px;
            font-size:16px;">
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

# ================= SIGNAL =================
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

c1.text_input("Strike", data["signal"]["Strike"])
c2.text_input("Entry", data["signal"]["Entry"])
c3.text_input("Target", data["signal"]["Target"])
c4.text_input("SL", data["signal"]["SL"])
c5.write(data["signal"]["Status"])

# ================= SUPPORT / RESISTANCE =================
st.subheader("📊 SUPPORT / RESISTANCE")

s1, s2 = st.columns(2)

s1.text_input("Support", data["sr"]["support"])
s2.text_input("Resistance", data["sr"]["resistance"])

# ================= OPTION CHAIN TABLE =================
atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

st.table(display_df[[
    "STRIKE",
    "open_interest_CE",
    "open_interest_PE",
    "volume_CE",
    "volume_PE"
]])
