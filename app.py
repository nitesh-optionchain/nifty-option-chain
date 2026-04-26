from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ================= PAGE =================
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")

# ================= SESSION =================
if "auth" not in st.session_state:
    st.session_state.auth = False

if "user" not in st.session_state:
    st.session_state.user = "Guest"

# ================= LOGIN =================
if not st.session_state.auth:

    st.title("🛡️ LOGIN PANEL")

    user = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")

    if st.button("LOGIN"):

        if user.strip() == "admin" and pwd.strip() == "1234":

            st.session_state.auth = True
            st.session_state.user = "Admin"

            st.success("Login Successful 🚀")
            st.rerun()

        else:
            st.error("Wrong Credentials")

    st.stop()

# ================= AUTO REFRESH =================
st_autorefresh(interval=5000, key="refresh")

# ================= HEADER =================
st.title("🚀 SMART WEALTH AI DASHBOARD")

st.sidebar.write(f"👤 User: {st.session_state.user}")

# ================= SDK INIT =================
if "sdk" not in st.session_state:
    st.session_state.sdk = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.sdk)

# ================= INDEX =================
index = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
exchange = "NSE" if index == "NIFTY" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.auth = False
    st.rerun()

# ================= DATA =================
st.subheader(f"📊 {index} OPTION CHAIN")

try:
    result = market.option_chain(index, exchange=exchange)
except Exception as e:
    st.error(f"API Error: {e}")
    st.stop()

if not result or not result.chain:
    st.warning("No Data Found")
    st.stop()

chain = result.chain

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE", "_PE")).fillna(0)

df["STRIKE"] = (df["strike_price"] / 100).astype(int)

# ================= SPOT =================
st.write("### Option Chain Data")
st.dataframe(df, use_container_width=True)
