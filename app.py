from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Option Chain Data", layout="wide")
st_autorefresh(interval=5000)

st.title("📊 Option Chain Data")

# =========================
# SIDEBAR
# =========================
symbol = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])

# =========================
# SESSION
# =========================
if "prev_data" not in st.session_state:
    st.session_state.prev_data = {}

if symbol not in st.session_state.prev_data:
    st.session_state.prev_data[symbol] = pd.DataFrame()

# =========================
# INIT
# =========================
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

# =========================
# FETCH
# =========================
def get_data(symbol):
    result = market_data.option_chain(symbol, exchange="NSE")
    if not result:
        return None

    chain = result.chain

    ce_df = pd.DataFrame([vars(x) for x in chain.ce])
    pe_df = pd.DataFrame([vars(x) for x in chain.pe])

    df = pd.merge(
        ce_df[["strike_price","open_interest","volume"]],
        pe_df[["strike_price","open_interest","volume"]],
        on="strike_price",
        suffixes=("_CE","_PE")
    )

    df["STRIKE"] = (df["strike_price"]/100).astype(int)
    atm = int(chain.at_the_money_strike/100)

    return df.sort_values("STRIKE").reset_index(drop=True), atm

# =========================
# FORMAT
# =========================
def pct_format(pct):
    if pct > 0:
        return f"+{pct:.2f}% ↑"
    elif pct < 0:
        return f"{pct:.2f}% ↓"
    else:
        return "0.00% —"

# =========================
# PROCESS
# =========================
def process(symbol, df):

    prev = st.session_state.prev_data[symbol]

    df = df.set_index("STRIKE")

    if not prev.empty:
        prev = prev.reindex(df.index)

        df["CE ΔOI"] = (df["open_interest_CE"] - prev["open_interest_CE"]).fillna(0)
        df["PE ΔOI"] = (df["open_interest_PE"] - prev["open_interest_PE"]).fillna(0)

        df["CE ΔVOL"] = (df["volume_CE"] - prev["volume_CE"]).fillna(0)
        df["PE ΔVOL"] = (df["volume_PE"] - prev["volume_PE"]).fillna(0)

    else:
        df["CE ΔOI"] = 0
        df["PE ΔOI"] = 0
        df["CE ΔVOL"] = 0
        df["PE ΔVOL"] = 0

    df = df.reset_index()

    # TOTAL VOL
    df["TOTAL VOL"] = df["volume_CE"] + df["volume_PE"]

    if not prev.empty:
        prev_total = (prev["volume_CE"] + prev["volume_PE"]).reindex(df["STRIKE"]).fillna(0)
        delta = df["TOTAL VOL"] - prev_total.values
    else:
        delta = 0

    df["TOTAL VOL %"] = (delta / df["TOTAL VOL"].replace(0,1) * 100)
    df["TOTAL VOL %"] = df["TOTAL VOL %"].apply(pct_format)

    # SIGNAL
    df["SIGNAL"] = "⚪ NORMAL"
    df.loc[(df["PE ΔOI"] > 0) & (df["PE ΔVOL"] > 0), "SIGNAL"] = "🟢 BUY"
    df.loc[(df["CE ΔOI"] > 0) & (df["CE ΔVOL"] > 0), "SIGNAL"] = "🔴 SELL"

    # SAVE
    st.session_state.prev_data[symbol] = df[[
        "STRIKE","open_interest_CE","open_interest_PE","volume_CE","volume_PE"
    ]].copy().set_index("STRIKE")

    return df

# =========================
# MAIN
# =========================
data = get_data(symbol)
if not data:
    st.stop()

df, atm = data
df = process(symbol, df)

atm_idx = df.index[df["STRIKE"] == atm][0]
top10 = df.iloc[max(atm_idx-5,0):atm_idx+5]

res = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
sup = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

display_df = top10[[
    "volume_CE",
    "STRIKE",
    "TOTAL VOL",
    "TOTAL VOL %",
    "volume_PE",
    "SIGNAL"
]]

# =========================
# STYLE
# =========================
def style(row):
    styles = []

    for col in display_df.columns:

        if col == "STRIKE":
            if row[col] == atm:
                styles.append("background-color:yellow;font-weight:bold")
            elif row[col] == res:
                styles.append("background-color:#00cc66;color:white")
            elif row[col] == sup:
                styles.append("background-color:#ff3333;color:white")
            else:
                styles.append("")

        elif col == "TOTAL VOL %":
            if "↑" in row[col]:
                styles.append("background-color:#00cc66;color:white;font-weight:bold")
            elif "↓" in row[col]:
                styles.append("background-color:#ff3333;color:white;font-weight:bold")
            else:
                styles.append("")

        elif col == "SIGNAL":
            if "BUY" in row[col]:
                styles.append("color:green;font-weight:bold")
            elif "SELL" in row[col]:
                styles.append("color:red;font-weight:bold")
            else:
                styles.append("")

        else:
            styles.append("")

    return styles

# METRICS
c1, c2, c3 = st.columns(3)
c1.metric("ATM", atm)
c2.metric("Resistance", int(res))
c3.metric("Support", int(sup))

# TABLE
st.dataframe(
    display_df.style.apply(style, axis=1),
    use_container_width=True,
    height=600
)

st.success(f"{symbol} Option Chain Running")
