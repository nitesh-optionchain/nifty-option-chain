import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# ================= CONFIG =================
st.set_page_config(layout="wide")

# Auto refresh every 5 sec
st_autorefresh(interval=5000, key="refresh")

# ================= AUTH =================
nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
md = MarketData(nubra)

# ================= INDEX HEADER =================
def get_index(symbol):
    data = md.current_price(symbol)
    price = data.price / 100
    change = data.change
    return price, change

cols = st.columns(3)
symbols = ["NIFTY", "BANKNIFTY", "SENSEX"]

for i, sym in enumerate(symbols):
    price, change = get_index(sym)
    color = "green" if change > 0 else "red"

    cols[i].markdown(
        f"""
        <h3>{sym}</h3>
        <h1 style='color:{color}'>{price:.2f}</h1>
        <h4>{change:.2f}%</h4>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ================= TIMEFRAME =================
tf = st.selectbox("Timeframe", ["1m","5m","15m","1h","1d"])

# ================= DATA =================
def get_data():
    res = md.historical_data({
        "exchange": "NSE",
        "type": "INDEX",
        "values": ["NIFTY"],
        "fields": ["open","high","low","close","cumulative_volume"],
        "startDate": "2026-05-01T03:30:00.000Z",
        "endDate": datetime.utcnow().isoformat()+"Z",
        "interval": tf,
        "intraDay": True,
        "realTime": False
    })

    stock = res.result[0].values[0]["NIFTY"]

    df = pd.DataFrame({
        "open": [x.value for x in stock.open],
        "high": [x.value for x in stock.high],
        "low": [x.value for x in stock.low],
        "close": [x.value for x in stock.close],
        "volume": [x.value for x in stock.cumulative_volume],
    })

    return df / 100

df = get_data()

# ================= RSI =================
def rsi(data, period=14):
    delta = data.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df["RSI"] = rsi(df["close"])

# ================= SUPER TREND =================
def supertrend(df, period=10, mult=3):
    hl2 = (df.high + df.low) / 2
    atr = (df.high - df.low).rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    return upper, lower

df["ST_up"], df["ST_down"] = supertrend(df)

# ================= VOLUME SPIKE =================
df["vol_avg"] = df["volume"].rolling(20).mean()
df["vol_spike"] = df["volume"] > df["vol_avg"] * 2

# ================= BORING CANDLE =================
df["body"] = abs(df["close"] - df["open"])
df["range"] = df["high"] - df["low"]
df["boring"] = df["body"] < (df["range"] * 0.3)

# ================= SUPPORT RESISTANCE =================
df["resistance"] = df["high"].rolling(20).max()
df["support"] = df["low"].rolling(20).min()

# ================= CHART =================
fig = go.Figure()

fig.add_trace(go.Candlestick(
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="Price"
))

fig.add_trace(go.Scatter(y=df["resistance"], name="Resistance", line=dict(color="blue", width=3)))
fig.add_trace(go.Scatter(y=df["support"], name="Support", line=dict(color="maroon", width=3)))

fig.add_trace(go.Scatter(y=df["ST_up"], name="ST Up"))
fig.add_trace(go.Scatter(y=df["ST_down"], name="ST Down"))

st.plotly_chart(fig, use_container_width=True)

# ================= RSI =================
st.subheader("RSI")
st.line_chart(df["RSI"])

# ================= OPTION CHAIN =================
st.subheader("Option Chain")

chain = md.option_chain("NIFTY")

ce = pd.DataFrame([vars(x) for x in chain.chain.ce])
pe = pd.DataFrame([vars(x) for x in chain.chain.pe])

df_chain = pd.DataFrame({
    "CE Vol": ce["volume"],
    "CE OI": ce["open_interest"],
    "CE OI Chg": ce["open_interest_change"],
    "Strike": ce["strike_price"],
    "PE OI": pe["open_interest"],
    "PE OI Chg": pe["open_interest_change"],
    "PE Vol": pe["volume"],
})

# ================= COLOR LOGIC =================
def color_chain(row):
    styles = []
    for col in row.index:
        val = row[col]

        if col == "CE Vol" and val == df_chain["CE Vol"].max():
            styles.append("background-color: darkgreen")
        elif col == "PE Vol" and val == df_chain["PE Vol"].max():
            styles.append("background-color: darkred")
        elif "CE OI" in col and val > df_chain["CE OI"].max()*0.75:
            styles.append("background-color: orange")
        elif "PE OI" in col and val > df_chain["PE OI"].max()*0.75:
            styles.append("background-color: pink")
        else:
            styles.append("")
    return styles

st.dataframe(df_chain.style.apply(color_chain, axis=1))

# ================= ADMIN =================
st.sidebar.title("Admin")

admins = ["9304768496", "7982046438"]
user = st.sidebar.text_input("Mobile")

if user in admins:
    st.sidebar.success("Admin Access")

    strike = st.sidebar.text_input("Strike")
    entry = st.sidebar.text_input("Entry")
    target = st.sidebar.text_input("Target")
    sl = st.sidebar.text_input("SL")

    if st.sidebar.button("Broadcast"):
        st.session_state["trade"] = {
            "Strike": strike,
            "Entry": entry,
            "Target": target,
            "SL": sl
        }

# ================= VIEWERS =================
st.subheader("Live Trade Signal")

if "trade" in st.session_state:
    st.success(st.session_state["trade"])
else:
    st.warning("No Signal")
