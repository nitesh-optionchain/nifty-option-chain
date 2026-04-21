from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# ================= USER DB =================
USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {
        "admin": {"pass": "1234", "role": "admin"}
    }

def save_users(data):
    with open(USER_FILE, "w") as f:
        json.dump(data, f)

users = load_users()

# ================= LOGIN =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_page():
    st.title("🔐 Secure Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in users and users[u]["pass"] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.session_state.role = users[u]["role"]
            st.success("Login Success")
            st.rerun()
        else:
            st.error("Access Denied")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ================= ADMIN USER CONTROL =================
if st.session_state.role == "admin":
    st.sidebar.subheader("👨‍💼 Admin Panel")

    new_user = st.sidebar.text_input("New Username")
    new_pass = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Add User"):
        users[new_user] = {"pass": new_pass, "role": "user"}
        save_users(users)
        st.sidebar.success("User Added")

    del_user = st.sidebar.selectbox("Delete User", list(users.keys()))
    if st.sidebar.button("Delete"):
        if del_user != "admin":
            users.pop(del_user)
            save_users(users)
            st.sidebar.success("User Deleted")

# ================= LOGOUT =================
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
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

try:
    nifty_live = chain.ce[0].underlying_price / 100
except:
    nifty_live = chain.at_the_money_strike / 100

# ================= HEADER =================
st.title("🛡️ SMART WEALTH AI 5")

chart_url = "https://www.tradingview.com/chart/?symbol=NSE:NIFTY"

c1, c2 = st.columns([3,1])

with c1:
    st.subheader(f"📊 LIVE NIFTY: {nifty_live:,.2f}")

with c2:
    st.markdown(f"""
    <a href="{chart_url}" target="_blank">
        <button style="width:100%;background:#2962ff;color:white;padding:10px;border:none;border-radius:6px;">
        📈 Open Chart
        </button>
    </a>
    """, unsafe_allow_html=True)

# ================= OPTION CHAIN =================
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

    df["oi_chg_CE"] = curr["open_interest_CE"].sub(prev["open_interest_CE"], fill_value=0).values
    df["oi_chg_PE"] = curr["open_interest_PE"].sub(prev["open_interest_PE"], fill_value=0).values
else:
    df["oi_chg_CE"] = df["oi_chg_PE"] = 0

st.session_state.prev_df = df.copy()

# ================= TABLE =================
def format_val(val, delta, m):
    p = (val/m*100) if m>0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

atm = int(nifty_live)
atm_idx = df.index[df["STRIKE"] >= atm][0]
d = df.iloc[max(atm_idx-7,0): atm_idx+8]

ui = pd.DataFrame()
ui["CE OI"] = d.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
ui["STRIKE"] = d["STRIKE"]
ui["PE OI"] = d.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)

st.table(ui)
