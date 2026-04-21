from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os
import plotly.graph_objects as go
import datetime

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

# ================= REAL TIME CANDLESTICK =================
if "candles" not in st.session_state:
    st.session_state.candles = []
    st.session_state.last_price = spot

current_time = datetime.datetime.now().strftime("%H:%M:%S")

prev_price = st.session_state.last_price

if len(st.session_state.candles) == 0:
    st.session_state.candles.append({
        "time": current_time,
        "open": spot,
        "high": spot,
        "low": spot,
        "close": spot
    })
else:
    last = st.session_state.candles[-1]

    last["high"] = max(last["high"], spot)
    last["low"] = min(last["low"], spot)
    last["close"] = spot

    st.session_state.candles.append({
        "time": current_time,
        "open": prev_price,
        "high": spot,
        "low": spot,
        "close": spot
    })

st.session_state.candles = st.session_state.candles[-30:]
st.session_state.last_price = spot

df_candle = pd.DataFrame(st.session_state.candles)

st.subheader("📊 LIVE NIFTY CANDLESTICK")

fig = go.Figure(data=[go.Candlestick(
    x=df_candle["time"],
    open=df_candle["open"],
    high=df_candle["high"],
    low=df_candle["low"],
    close=df_candle["close"]
)])

fig.update_layout(height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# ================= DATAFRAME =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ================= ADMIN SIGNAL =================
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

if is_admin:
    s_strike = c1.text_input("Strike", value=data["signal"]["Strike"])
    s_entry = c2.text_input("Entry", value=data["signal"]["Entry"])
    s_target = c3.text_input("Target", value=data["signal"]["Target"])
    s_sl = c4.text_input("SL", value=data["signal"]["SL"])

    if c5.button("📢 UPDATE"):
        data["signal"] = {
            "Strike": s_strike,
            "Entry": s_entry,
            "Target": s_target,
            "SL": s_sl,
            "Status": f"LIVE ({current_admin_name})"
        }
        save_data(data)

else:
    c1.info(data["signal"]["Strike"])
    c2.success(data["signal"]["Entry"])
    c3.warning(data["signal"]["Target"])
    c4.error(data["signal"]["SL"])
    c5.write(data["signal"]["Status"])

# ================= SUPPORT RESISTANCE =================
st.subheader("📊 SUPPORT / RESISTANCE")

s1, s2, s3 = st.columns(3)

if is_admin:
    sup = s1.text_input("Support", data["sr"]["support"])
    res = s2.text_input("Resistance", data["sr"]["resistance"])

    if s3.button("SET"):
        data["sr"] = {"support": sup, "resistance": res}
        save_data(data)

a, b = st.columns(2)
a.metric("🟢 SUPPORT", data["sr"]["support"])
b.metric("🔴 RESISTANCE", data["sr"]["resistance"])

# ================= OPTION CHAIN =================
st.subheader("📊 OPTION CHAIN")

st.dataframe(df.head(20))
