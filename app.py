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

st.title("📊 OPTION CHAIN DATA (EXACT DESIGN TABLE)")

# =========================
# SESSION
# =========================
if "prev" not in st.session_state:
    st.session_state.prev = None

# =========================
# INIT
# =========================
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md = MarketData(nubra)

# =========================
# FETCH
# =========================
res = md.option_chain("NIFTY", exchange="NSE")
if not res:
    st.stop()

chain = res.chain

# =========================
# DATA PREP
# =========================
ce = pd.DataFrame([vars(x) for x in chain.ce])
pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(
    ce[["strike_price","open_interest","volume"]],
    pe[["strike_price","open_interest","volume"]],
    on="strike_price",
    suffixes=("_CE","_PE")
)

df["STRIKE"] = (df["strike_price"]/100).astype(int)
atm = int(chain.at_the_money_strike/100)

df = df.sort_values("STRIKE").reset_index(drop=True)

# =========================
# CHANGE CALC
# =========================
if st.session_state.prev is not None:
    prev = st.session_state.prev.set_index("STRIKE")
    df = df.set_index("STRIKE")

    df["CE_OI_CHG"] = (df["open_interest_CE"] - prev["open_interest_CE"]).fillna(0)
    df["PE_OI_CHG"] = (df["open_interest_PE"] - prev["open_interest_PE"]).fillna(0)

    df["CE_VOL_CHG"] = (df["volume_CE"] - prev["volume_CE"]).fillna(0)
    df["PE_VOL_CHG"] = (df["volume_PE"] - prev["volume_PE"]).fillna(0)

    df = df.reset_index()
else:
    df["CE_OI_CHG"] = 0
    df["PE_OI_CHG"] = 0
    df["CE_VOL_CHG"] = 0
    df["PE_VOL_CHG"] = 0

st.session_state.prev = df.copy()

# =========================
# % CALC (IMPORTANT)
# =========================
df["CE_VOL_%"] = ((df["CE_VOL_CHG"]/(df["volume_CE"]+1))*100).round(2)
df["PE_VOL_%"] = ((df["PE_VOL_CHG"]/(df["volume_PE"]+1))*100).round(2)

# =========================
# ATM RANGE
# =========================
atm_idx = df.index[df["STRIKE"] == atm][0]
df = df.iloc[max(atm_idx-5,0):atm_idx+5]

# =========================
# FINAL DISPLAY STRUCTURE (MATCH IMAGE)
# =========================
display_df = pd.DataFrame({
    "OI Chg": df["CE_OI_CHG"],
    "OI": df["open_interest_CE"],
    "Volume": df["volume_CE"],
    "Vol %": df["CE_VOL_%"],

    "STRIKE": df["STRIKE"],

    "Volume ": df["volume_PE"],
    "Vol % ": df["PE_VOL_%"],
    "OI ": df["open_interest_PE"],
    "OI Chg ": df["PE_OI_CHG"],
})

# =========================
# COLOR STYLE
# =========================
def style(row):
    styles = []

    for col in display_df.columns:

        if col == "STRIKE" and row[col] == atm:
            styles.append("background-color:orange;font-weight:bold")

        elif "OI Chg" in col and row[col] > 0:
            styles.append("color:green")

        elif "OI Chg" in col and row[col] < 0:
            styles.append("color:red")

        elif "Vol %" in col and row[col] > 20:
            styles.append("background-color:yellow")

        else:
            styles.append("")

    return styles

# =========================
# TABLE
# =========================
st.dataframe(
    display_df.style.apply(style, axis=1),
    use_container_width=True,
    height=500
)

st.success("✅ Exact Design Data Showing")
