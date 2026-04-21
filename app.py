from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="auto")

# ==========================================
# SDK LOGIN
# ==========================================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

nubra = st.session_state.nubra
market_data = MarketData(nubra)

# ==========================================
# DATA FETCH
# ==========================================
result = market_data.option_chain("NIFTY", exchange="NSE")
if not result:
    st.stop()

chain = result.chain
spot = chain.at_the_money_strike / 100
atm = int(spot)

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE"))
df = df.fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ==========================================
# BASIC METRICS
# ==========================================
total_ce = df["open_interest_CE"].sum()
total_pe = df["open_interest_PE"].sum()
pcr = round(total_pe / total_ce, 2) if total_ce != 0 else 0

# ==========================================
# 🔥 SMART SIGNAL LOGIC
# ==========================================
signal_text = "WAITING"
entry = target = sl = "-"
confidence = "LOW"

try:
    max_ce_oi_strike = df.loc[df["open_interest_CE"].idxmax()]["STRIKE"]
    max_pe_oi_strike = df.loc[df["open_interest_PE"].idxmax()]["STRIKE"]

    atm_row = df[df["STRIKE"] == atm].iloc[0]

    ce_price = atm_row["last_traded_price_CE"]
    pe_price = atm_row["last_traded_price_PE"]

    ce_oi = atm_row["open_interest_CE"]
    pe_oi = atm_row["open_interest_PE"]

    # 🔥 CE BUY
    if pcr > 1 and pe_oi > ce_oi:
        signal_text = f"BUY CE {atm}"
        entry = round(ce_price, 1)
        target = round(ce_price * 1.4, 1)
        sl = round(ce_price * 0.75, 1)
        confidence = "HIGH"

    # 🔥 PE BUY
    elif pcr < 0.8 and ce_oi > pe_oi:
        signal_text = f"BUY PE {atm}"
        entry = round(pe_price, 1)
        target = round(pe_price * 1.4, 1)
        sl = round(pe_price * 0.75, 1)
        confidence = "HIGH"

except:
    pass

# ==========================================
# HEADER
# ==========================================
st.title("🛡️ SMART WEALTH AI 5")

c1, c2, c3, c4 = st.columns(4)
c1.metric("NIFTY SPOT", f"{spot:,.2f}")
c2.metric("PCR", pcr)
c3.metric("SMART SIGNAL", signal_text)
c4.metric("CONFIDENCE", confidence)

# SIGNAL DETAILS
st.info(f"Entry: {entry} | Target: {target} | SL: {sl}")

# ==========================================
# OPTION CHAIN UI
# ==========================================
max_ce_vol = df["volume_CE"].max()
max_pe_vol = df["volume_PE"].max()
max_ce_oi = df["open_interest_CE"].max()
max_pe_oi = df["open_interest_PE"].max()

def format_val(val, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n{p:.1f}%"

atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8]

ui = pd.DataFrame()
ui["CE OI"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], max_ce_oi), axis=1)
ui["CE VOL"] = display_df.apply(lambda r: format_val(r["volume_CE"], max_ce_vol), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL"] = display_df.apply(lambda r: format_val(r["volume_PE"], max_pe_vol), axis=1)
ui["PE OI"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], max_pe_oi), axis=1)

# ==========================================
# 🎨 FINAL COLOR LOGIC
# ==========================================
def style(row):
    s = ['']*len(row)

    try:
        ce_oi = float(row[0].split('\n')[1].replace('%',''))
        ce_vol = float(row[1].split('\n')[1].replace('%',''))
        pe_vol = float(row[3].split('\n')[1].replace('%',''))
        pe_oi = float(row[4].split('\n')[1].replace('%',''))

        # CE BLUE
        if ce_oi > 65 and ce_vol > 70:
            s[0] = s[1] = 'background-color: #0d47a1; color:white'

        # PE ORANGE
        if pe_oi > 65 and pe_vol > 70:
            s[3] = s[4] = 'background-color: #ff6f00; color:white'

        # CE HIGH VOL
        if ce_vol == 100:
            s[1] = 'background-color: green; color:white'

        # PE HIGH VOL
        if pe_vol == 100:
            s[3] = 'background-color: red; color:white'

        # ATM
        if row[2] == atm:
            s[2] = 'background-color: yellow; color:black; font-weight:bold'

        # NEAR ATM
        elif abs(row[2] - atm) <= 100:
            s[2] = 'background-color: #eeeeee'

    except:
        pass

    return s

st.table(ui.style.apply(style, axis=1))
