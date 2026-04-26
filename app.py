from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker.websocketdata import NubraDataSocket

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ================= PAGE CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# ================= SESSION INIT =================
if "auth" not in st.session_state:
    st.session_state.auth = False

if "user" not in st.session_state:
    st.session_state.user = "Guest"

if "live" not in st.session_state:
    st.session_state.live = {
        "NIFTY": 0,
        "SENSEX": 0,
        "BANKNIFTY": 0
    }

# ================= LOGIN =================
def login_page():

    st.title("🛡️ SMART WEALTH AI LOGIN")

    user = st.text_input("User ID", key="u1")
    pwd = st.text_input("Password", type="password", key="p1")

    if st.button("LOGIN"):

        if user.strip() == "admin" and pwd.strip() == "1234":

            st.session_state.auth = True
            st.session_state.user = "Admin"

            st.success("Login Success 🚀")
            st.rerun()

        else:
            st.error("Invalid Credentials")

    st.stop()

if not st.session_state.auth:
    login_page()

# ================= AUTO REFRESH =================
st_autorefresh(interval=5000, key="refresh")

# ================= HEADER =================
st.title("🚀 SMART WEALTH AI DASHBOARD")

st.sidebar.write(f"👤 User: {st.session_state.user}")

# ================= SDK =================
if "sdk" not in st.session_state:
    st.session_state.sdk = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.sdk)

# ================= WEBSOCKET =================
def on_tick(msg):
    try:
        name = getattr(msg, "indexname", None)
        value = getattr(msg, "index_value", 0)

        if name:
            st.session_state.live[name] = float(value)

    except Exception:
        pass

if "socket" not in st.session_state:
    try:
        socket = NubraDataSocket(
            client=st.session_state.sdk,
            on_index_data=on_tick
        )
        socket.connect()
        socket.subscribe(
            ["NIFTY", "SENSEX", "BANKNIFTY"],
            data_type="index",
            exchange="NSE"
        )
        st.session_state.socket = socket
    except Exception as e:
        st.warning(f"WebSocket Warning: {e}")

# ================= LIVE HEADER =================
c1, c2, c3 = st.columns(3)

c1.metric("NIFTY", st.session_state.live["NIFTY"])
c2.metric("SENSEX", st.session_state.live["SENSEX"])
c3.metric("BANKNIFTY", st.session_state.live["BANKNIFTY"])

# ================= INDEX SELECT =================
index_choice = st.sidebar.selectbox(
    "Select Index",
    ["NIFTY", "SENSEX", "BANKNIFTY"]
)

exchange = "NSE" if index_choice != "SENSEX" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.auth = False
    st.rerun()

# ================= OPTION CHAIN =================
st.subheader(f"📊 {index_choice} OPTION CHAIN")

try:
    result = market.option_chain(index_choice, exchange=exchange)
except Exception as e:
    st.error(f"API Error: {e}")
    st.stop()

if not result or not result.chain:
    st.warning("No Data Available")
    st.stop()

chain = result.chain

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE", "_PE"))

df["STRIKE"] = (df["strike_price"] / 100).astype(int)

df = df.sort_values("STRIKE").reset_index(drop=True)

# ================= SPOT =================
st.write(f"📍 Selected Index: {index_choice}")

# ================= TABLE =================
st.dataframe(df, use_container_width=True)
