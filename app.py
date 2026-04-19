from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ==========================
# CONFIG
# ==========================
st.set_page_config(page_title="NIFTY PRO - ADMIN PANEL", layout="wide")
st_autorefresh(interval=5000, key="pro_final_v3")

# ==========================
# ADMIN DB
# ==========================
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
    st.sidebar.success(f"⚡ Auto-Logged in: {current_admin_name}")
else:
    with st.sidebar.expander("🔑 Admin Login"):
        user_key = st.text_input("Enter Mobile ID:", type="password")
        if user_key in ADMIN_DB:
            is_admin = True
            current_admin_name = ADMIN_DB[user_key]
            st.sidebar.success(f"✅ Welcome: {current_admin_name}")

# ==========================
# SESSION STATE
# ==========================
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

if "signal" not in st.session_state:
    st.session_state.signal = {
        "Strike": "-",
        "Entry": "-",
        "Target": "-",
        "SL": "-",
        "Status": "WAITING"
    }

# ==========================
# SAFE SDK INIT
# ==========================
if "nubra" not in st.session_state:
    try:
        st.session_state.nubra = InitNubraSdk(
            NubraEnv.UAT,
            env_creds=False
        )
    except Exception as e:
        st.error(f"SDK INIT FAILED: {e}")
        st.stop()

nubra = st.session_state.nubra

# ==========================
# SAFE MARKET DATA INIT
# ==========================
try:
    market_data = MarketData(nubra)
except Exception as e:
    st.error(f"MarketData INIT FAILED: {e}")
    st.stop()

# ==========================
# FETCH DATA
# ==========================
try:
    result = market_data.option_chain("NIFTY", exchange="NSE")
except Exception as e:
    st.error(f"API ERROR: {e}")
    st.stop()

if not result:
    st.warning("No data received")
    st.stop()

chain = result.chain
spot = chain.at_the_money_strike / 100
atm = int(spot)

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE", "_PE"))
df["STRIKE"] = (df["strike_price"] / 100).astype(int)

# ==========================
# CHANGE TRACKING
# ==========================
if st.session_state.prev_df is not None:
    prev = st.session_state.prev_df.set_index("STRIKE")
    curr = df.set_index("STRIKE")

    df["oi_chg_CE"] = df["STRIKE"].map(
        curr["open_interest_CE"] - prev["open_interest_CE"]
    ).fillna(0)

    df["oi_chg_PE"] = df["STRIKE"].map(
        curr["open_interest_PE"] - prev["open_interest_PE"]
    ).fillna(0)
else:
    df["oi_chg_CE"] = 0
    df["oi_chg_PE"] = 0

st.session_state.prev_df = df.copy()

# ==========================
# DASHBOARD
# ==========================
pcr = round(df["open_interest_PE"].sum() / df["open_interest_CE"].sum(), 2)

st.title("🛡️ NIFTY LIVE DASHBOARD")

c1, c2, c3 = st.columns(3)
c1.metric("SPOT", f"{spot:,.2f}")
c2.metric("PCR", pcr)
c3.metric("STATUS", "BULLISH" if pcr > 0.8 else "BEARISH")

# ==========================
# SIGNAL PANEL
# ==========================
st.markdown("---")
st.subheader("🎯 TRADE SIGNAL")

if is_admin:
    s1, s2, s3, s4, s5 = st.columns(5)

    with s1:
        strike = st.text_input("Strike", st.session_state.signal["Strike"])
    with s2:
        entry = st.text_input("Entry", st.session_state.signal["Entry"])
    with s3:
        target = st.text_input("Target", st.session_state.signal["Target"])
    with s4:
        sl = st.text_input("SL", st.session_state.signal["SL"])
    with s5:
        if st.button("UPDATE"):
            st.session_state.signal = {
                "Strike": strike,
                "Entry": entry,
                "Target": target,
                "SL": sl,
                "Status": f"LIVE ({current_admin_name})"
            }
else:
    st.info(st.session_state.signal)

# ==========================
# TABLE
# ==========================
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx - 7, 0): atm_idx + 8]

final_df = display_df[[
    "STRIKE",
    "open_interest_CE",
    "open_interest_PE",
    "volume_CE",
    "volume_PE"
]]

st.dataframe(final_df, use_container_width=True)
