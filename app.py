from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# ================= ADMIN =================
ADMIN_DB = {
    "9304768496": "Admin Chief", 
    "7982046438": "Rupesh Kumar",
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

# ================= SESSION =================
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}

if "sr" not in st.session_state:
    st.session_state.sr = {"support": "-", "resistance": "-"}

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
spot = getattr(chain, "underlying_value", None)
prev_close = getattr(chain, "previous_close", None)

st.title("🛡️ SMART WEALTH AI 5")

c1, c2 = st.columns(2)

if spot is not None and prev_close:
    change = spot - prev_close
    change_pct = (change / prev_close) * 100
    c1.metric("📊 NIFTY LIVE", f"{spot:,.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
else:
    spot = chain.at_the_money_strike / 100
    c1.metric("📊 NIFTY (Fallback)", f"{spot:,.2f}")

# ================= DATAFRAME =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ================= CHANGE TRACK =================
if st.session_state.prev_df is not None:
    prev = st.session_state.prev_df.set_index("STRIKE")
    curr = df.set_index("STRIKE")

    df["oi_chg_CE"] = df["STRIKE"].map(curr["open_interest_CE"] - prev["open_interest_CE"]).fillna(0)
    df["oi_chg_PE"] = df["STRIKE"].map(curr["open_interest_PE"] - prev["open_interest_PE"]).fillna(0)
    df["prc_chg_CE"] = df["STRIKE"].map(curr["last_traded_price_CE"] - prev["last_traded_price_CE"]).fillna(0)
    df["prc_chg_PE"] = df["STRIKE"].map(curr["last_traded_price_PE"] - prev["last_traded_price_PE"]).fillna(0)
else:
    df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0

st.session_state.prev_df = df.copy()

# ================= ADMIN SIGNAL =================
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

if is_admin:
    s_strike = c1.text_input("Strike", value=st.session_state.signal["Strike"], key="strike")
    s_entry = c2.text_input("Entry", value=st.session_state.signal["Entry"], key="entry")
    s_target = c3.text_input("Target", value=st.session_state.signal["Target"], key="target")
    s_sl = c4.text_input("SL", value=st.session_state.signal["SL"], key="sl")

    if c5.button("📢 UPDATE"):
        st.session_state.signal["Strike"] = s_strike
        st.session_state.signal["Entry"] = s_entry
        st.session_state.signal["Target"] = s_target
        st.session_state.signal["SL"] = s_sl
        st.session_state.signal["Status"] = f"LIVE ({current_admin_name})"

else:
    c1.info(st.session_state.signal["Strike"])
    c2.success(st.session_state.signal["Entry"])
    c3.warning(st.session_state.signal["Target"])
    c4.error(st.session_state.signal["SL"])
    c5.write(st.session_state.signal["Status"])

# ================= SUPPORT RESISTANCE =================
st.subheader("📊 SUPPORT / RESISTANCE")

s1, s2, s3 = st.columns(3)

if is_admin:
    sup = s1.text_input("Support", st.session_state.sr["support"])
    res = s2.text_input("Resistance", st.session_state.sr["resistance"])

    if s3.button("SET"):
        st.session_state.sr = {"support": sup, "resistance": res}

a, b = st.columns(2)
a.metric("🟢 SUPPORT", st.session_state.sr["support"])
b.metric("🔴 RESISTANCE", st.session_state.sr["resistance"])

# ================= OPTION CHAIN =================
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

# ================= COLOR =================
def final_style(row):
    styles = [''] * len(row)

    try:
        ce_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
        ce_vol = float(row.iloc[2].split('\n')[-1].replace('%',''))
        pe_vol = float(row.iloc[4].split('\n')[-1].replace('%',''))
        pe_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))

        if ce_oi > 65:
            styles[1] = 'background-color:#0d47a1;color:white'

        if ce_vol >= 90:
            styles[2] = 'background-color:#00c853;color:white'

        if pe_oi > 65:
            styles[5] = 'background-color:#ff6f00;color:white'

        if pe_vol >= 90:
            styles[4] = 'background-color:#d50000;color:white'

        if row.iloc[3] == atm:
            styles[3] = 'background-color:yellow;color:black;font-weight:bold'
        else:
            styles[3] = 'background-color:#eeeeee'

    except:
        pass

    return styles

st.table(ui.style.apply(final_style, axis=1))
