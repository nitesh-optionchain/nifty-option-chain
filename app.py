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
# ADMIN SYSTEM
# ==========================================
ADMIN_DB = {
    "9304768496": "Admin Chief",
    "7982048438": "Rupesh Kumar",
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

# ==========================================
# SESSION STATES
# ==========================================
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

if "manual_signal" not in st.session_state:
    st.session_state.manual_signal = {
        "type": "-",
        "entry": "-",
        "target": "-",
        "sl": "-",
        "conf": "WAITING"
    }

if "sr_levels" not in st.session_state:
    st.session_state.sr_levels = {
        "support": "-",
        "resistance": "-"
    }

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

# ==========================================
# LIVE NIFTY
# ==========================================
try:
    ltp = chain.underlying_ltp
    prev = chain.prev_close
    change = ltp - prev
    pct = (change / prev) * 100 if prev != 0 else 0
    nifty_text = f"{ltp:,.2f} ({change:+.2f} / {pct:+.2f}%)"
except:
    nifty_text = f"{spot:,.2f}"

# ==========================================
# VIX
# ==========================================
try:
    vix = chain.india_vix
except:
    vix = "-"

# ==========================================
# DATAFRAME
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE"))
df = df.fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ==========================================
# CHANGE TRACKING
# ==========================================
if st.session_state.prev_df is not None:
    prev_df = st.session_state.prev_df.set_index("STRIKE")
    curr_df = df.set_index("STRIKE")

    df["oi_chg_CE"] = df["STRIKE"].map(curr_df["open_interest_CE"] - prev_df["open_interest_CE"]).fillna(0)
    df["oi_chg_PE"] = df["STRIKE"].map(curr_df["open_interest_PE"] - prev_df["open_interest_PE"]).fillna(0)
    df["prc_chg_CE"] = df["STRIKE"].map(curr_df["last_traded_price_CE"] - prev_df["last_traded_price_CE"]).fillna(0)
    df["prc_chg_PE"] = df["STRIKE"].map(curr_df["last_traded_price_PE"] - prev_df["last_traded_price_PE"]).fillna(0)
else:
    df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0

st.session_state.prev_df = df.copy()

# ==========================================
# HEADER
# ==========================================
total_ce = df["open_interest_CE"].sum()
total_pe = df["open_interest_PE"].sum()
pcr = round(total_pe / total_ce, 2) if total_ce != 0 else 0

st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY", nifty_text)
m2.metric("PCR", pcr)
m3.metric("VIX", vix)
m4.metric("STATUS", "📈 NORMAL" if pcr > 0.8 else "📉 BEARISH")

# ==========================================
# SUPPORT RESISTANCE (MANUAL)
# ==========================================
st.markdown("---")
st.subheader("📊 SUPPORT / RESISTANCE")

c1, c2, c3 = st.columns(3)

if is_admin:
    sup_in = c1.text_input("Support", st.session_state.sr_levels["support"])
    res_in = c2.text_input("Resistance", st.session_state.sr_levels["resistance"])

    if c3.button("UPDATE LEVELS"):
        st.session_state.sr_levels = {"support": sup_in, "resistance": res_in}

sup = st.session_state.sr_levels["support"]
res = st.session_state.sr_levels["resistance"]

s1, s2 = st.columns(2)
s1.metric("🟢 SUPPORT", sup)
s2.metric("🔴 RESISTANCE", res)

# ==========================================
# TRADE SIGNAL
# ==========================================
st.markdown("---")
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

if is_admin:
    s_strike = c1.text_input("Strike", st.session_state.manual_signal["type"])
    s_entry = c2.text_input("Entry", st.session_state.manual_signal["entry"])
    s_target = c3.text_input("Target", st.session_state.manual_signal["target"])
    s_sl = c4.text_input("SL", st.session_state.manual_signal["sl"])

    if c5.button("📢 UPDATE"):
        st.session_state.manual_signal = {
            "type": s_strike,
            "entry": s_entry,
            "target": s_target,
            "sl": s_sl,
            "conf": f"LIVE ({current_admin_name})"
        }

sig = st.session_state.manual_signal

d1, d2, d3, d4, d5 = st.columns(5)
d1.info(f"📌 {sig['type']}")
d2.success(f"ENTRY\n{sig['entry']}")
d3.warning(f"TARGET\n{sig['target']}")
d4.error(f"SL\n{sig['sl']}")
d5.write(f"STATUS\n{sig['conf']}")

# ==========================================
# OPTION CHAIN
# ==========================================
max_ce_vol = df["volume_CE"].max()
max_pe_vol = df["volume_PE"].max()
max_ce_oi = df["open_interest_CE"].max()
max_pe_oi = df["open_interest_PE"].max()

def format_val(val, m):
    p = (val/m*100) if m > 0 else 0
    return f"{val:,.0f}\n{p:.1f}%"

atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE OI"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], max_ce_oi), axis=1)
ui["CE VOL"] = display_df.apply(lambda r: format_val(r["volume_CE"], max_ce_vol), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL"] = display_df.apply(lambda r: format_val(r["volume_PE"], max_pe_vol), axis=1)
ui["PE OI"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], max_pe_oi), axis=1)

def style(row):
    s = ['']*len(row)
    try:
        ce_oi = float(row[0].split('\n')[1].replace('%',''))
        ce_vol = float(row[1].split('\n')[1].replace('%',''))
        pe_vol = float(row[3].split('\n')[1].replace('%',''))
        pe_oi = float(row[4].split('\n')[1].replace('%',''))

        if ce_oi > 65 and ce_vol > 70:
            s[0] = s[1] = 'background-color:#0d47a1;color:white'

        if pe_oi > 65 and pe_vol > 70:
            s[3] = s[4] = 'background-color:#ff6f00;color:white'

        if ce_vol == 100:
            s[1] = 'background-color:green;color:white'

        if pe_vol == 100:
            s[3] = 'background-color:red;color:white'

        if row[2] == atm:
            s[2] = 'background-color:yellow;color:black;font-weight:bold'
        elif abs(row[2] - atm) <= 100:
            s[2] = 'background-color:#eeeeee'
    except:
        pass
    return s

st.table(ui.style.apply(style, axis=1))
