from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker.websocketdata import NubraDataSocket

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# ================= AUTH =================
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"
    st.session_state.is_super_admin = False

# LOGIN
if not st.session_state.is_auth:
    st.title("🛡️ SMART WEALTH AI 5 LOGIN")
    user = st.text_input("Enter ID", type="password")

    if st.button("LOGIN"):
        if user:
            st.session_state.is_auth = True
            st.session_state.admin_name = "Admin"
            st.rerun()
        else:
            st.error("Invalid Login")
    st.stop()

# ================= AUTO REFRESH =================
st_autorefresh(interval=5000, key="refresh")

# ================= SDK INIT =================
if "sdk" not in st.session_state:
    st.session_state.sdk = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.sdk)

# ================= LIVE DATA (STABLE WS) =================
if "live_data" not in st.session_state:
    st.session_state.live_data = {"NIFTY": 0, "SENSEX": 0}

def safe_tick(msg):
    try:
        name = getattr(msg, "indexname", None)
        value = getattr(msg, "index_value", 0)

        if name:
            st.session_state.live_data[name] = float(value)

    except Exception:
        pass

# SOCKET INIT
if "socket" not in st.session_state:
    socket = NubraDataSocket(
        client=st.session_state.sdk,
        on_index_data=safe_tick
    )
    socket.connect()
    socket.subscribe(["NIFTY", "SENSEX"], data_type="index", exchange="NSE")
    st.session_state.socket = socket

# ================= HEADER =================
st.title("🚀 SMART WEALTH AI 5 - FULL TERMINAL")

c1, c2 = st.columns(2)
c1.metric("📊 NIFTY LIVE", st.session_state.live_data.get("NIFTY", "WAIT"))
c2.metric("📊 SENSEX LIVE", st.session_state.live_data.get("SENSEX", "WAIT"))

# ================= INDEX =================
index_choice = st.sidebar.selectbox("INDEX", ["NIFTY", "SENSEX"])
exchange = "NSE" if index_choice == "NIFTY" else "BSE"

st.sidebar.write(f"👤 {st.session_state.admin_name}")

if st.sidebar.button("LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

# ================= LOAD DATA =================
st.subheader(f"📊 {index_choice} OPTION CHAIN")

try:
    result = market.option_chain(index_choice, exchange=exchange)
except Exception as e:
    st.error(f"API Error: {e}")
    st.stop()

if not result or not result.chain:
    st.warning("No Data Found")
    st.stop()

chain = result.chain

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ================= SPOT =================
spot = st.session_state.live_data.get(index_choice, 0)

st.write(f"📍 SPOT PRICE: {spot}")

# ================= OI CHANGE =================
df["oi_chg_CE"] = df["open_interest_CE"] - df["open_interest_CE"].shift(1).fillna(0)
df["oi_chg_PE"] = df["open_interest_PE"] - df["open_interest_PE"].shift(1).fillna(0)

# ================= MAX VALUES =================
max_oi_ce = df["open_interest_CE"].max()
max_oi_pe = df["open_interest_PE"].max()
max_vol_ce = df["volume_CE"].max()
max_vol_pe = df["volume_PE"].max()

# ================= BREAKOUT LEVEL =================
be_res = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
be_sup = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

# ================= ADMIN PANEL =================
if st.session_state.is_super_admin:
    with st.expander("🛠️ ADMIN PANEL"):
        strike = st.text_input("Strike")
        entry = st.text_input("Entry")
        target = st.text_input("Target")
        sl = st.text_input("SL")

        if st.button("SAVE SIGNAL"):
            st.success("Signal Saved")

# ================= TABLE =================
ui = df[["STRIKE","open_interest_CE","oi_chg_CE","volume_CE",
         "volume_PE","oi_chg_PE","open_interest_PE"]].copy()

st.dataframe(ui, use_container_width=True)

# ================= ALERT =================
if spot >= be_res:
    st.success(f"🚀 CALL SIDE BREAKOUT ABOVE {be_res}")
elif spot <= be_sup:
    st.error(f"🩸 PUT SIDE BREAKDOWN BELOW {be_sup}")
