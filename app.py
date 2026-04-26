from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker.websocketdata import NubraDataSocket

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ================= PAGE CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# ================= SESSION INIT =================
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if "admin_name" not in st.session_state:
    st.session_state.admin_name = "Guest"

if "live_data" not in st.session_state:
    st.session_state.live_data = {"NIFTY": 0, "SENSEX": 0}

# ================= LOGIN =================
if not st.session_state.is_auth:

    st.title("🛡️ SMART WEALTH AI 5 LOGIN")

    user = st.text_input("User ID", key="user")
    pwd = st.text_input("Password", type="password", key="pass")

    if st.button("LOGIN"):

        if user.strip() == "admin" and pwd.strip() == "1234":
            st.session_state.is_auth = True
            st.session_state.admin_name = "Admin"
            st.success("Login Successful 🚀")
            st.rerun()
        else:
            st.error("❌ Invalid Credentials")

    st.stop()

# ================= AUTO REFRESH =================
st_autorefresh(interval=5000, key="refresh")

# ================= SDK INIT =================
if "sdk" not in st.session_state:
    st.session_state.sdk = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.sdk)

# ================= SAFE WEBSOCKET =================
def safe_tick(msg):
    try:
        name = getattr(msg, "indexname", None)
        value = getattr(msg, "index_value", 0)

        if name:
            st.session_state.live_data[name] = float(value)

    except Exception:
        pass

if "socket" not in st.session_state:
    try:
        socket = NubraDataSocket(
            client=st.session_state.sdk,
            on_index_data=safe_tick
        )
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX"], data_type="index", exchange="NSE")
        st.session_state.socket = socket
    except Exception as e:
        st.warning(f"WebSocket Warning: {e}")

# ================= HEADER =================
st.title("🚀 SMART WEALTH AI 5 - LIVE DASHBOARD")

c1, c2 = st.columns(2)
c1.metric("📊 NIFTY LIVE", st.session_state.live_data.get("NIFTY", "WAIT"))
c2.metric("📊 SENSEX LIVE", st.session_state.live_data.get("SENSEX", "WAIT"))

st.sidebar.write(f"👤 User: {st.session_state.admin_name}")

# ================= INDEX SELECT =================
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
exchange = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.is_auth = False
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

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE", "_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"] / 100).astype(int)

# ================= SPOT =================
spot = st.session_state.live_data.get(index_choice, 0)
st.write(f"📍 Spot Price: {spot}")

# ================= OI CHANGE =================
df["oi_chg_CE"] = df["open_interest_CE"].diff().fillna(0)
df["oi_chg_PE"] = df["open_interest_PE"].diff().fillna(0)

# ================= BREAKOUT LEVELS =================
be_res = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
be_sup = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

# ================= ALERT =================
if spot >= be_res:
    st.success(f"🚀 CALL BREAKOUT ABOVE {be_res}")
elif spot <= be_sup:
    st.error(f"🩸 PUT BREAKDOWN BELOW {be_sup}")

# ================= FINAL TABLE =================
ui = df[[
    "STRIKE",
    "open_interest_CE",
    "oi_chg_CE",
    "volume_CE",
    "volume_PE",
    "oi_chg_PE",
    "open_interest_PE"
]]

st.dataframe(ui, use_container_width=True)
