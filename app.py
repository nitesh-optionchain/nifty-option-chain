from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ==========================================
# 1. CONFIG & REFRESH
# ==========================================
st.set_page_config(page_title="NIFTY PRO - ADMIN PANEL", layout="wide")
st_autorefresh(interval=5000, key="pro_final_v3")

# ==========================================
# 2. ADMIN & AUTH (UNCHANGED)
# ==========================================
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
    st.sidebar.success(f"⚡ Auto-Logged in: {current_admin_name}")
else:
    with st.sidebar.expander("🔑 Admin Login"):
        user_key = st.text_input("Enter Mobile ID:", type="password")
        if user_key in ADMIN_DB:
            is_admin = True
            current_admin_name = ADMIN_DB[user_key]
            st.sidebar.success(f"✅ Welcome: {current_admin_name}")

# ==========================================
# SESSION STATES (UNCHANGED)
# ==========================================
if "prev_df" not in st.session_state: st.session_state.prev_df = None
if "pcr_history" not in st.session_state: st.session_state.pcr_history = []
if "prev_total_vol" not in st.session_state: st.session_state.prev_total_vol = 0
if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}

# ==========================================
# 3. SDK LOGIN (🔥 FIXED)
# ==========================================
try:
    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

    nubra = st.session_state.nubra
    market_data = MarketData(nubra)

except Exception as e:
    st.error(f"❌ SDK Auth Failed: {e}")
    st.stop()

# ==========================================
# 4. DATA FETCH (SAFE FIX ADDED)
# ==========================================
result = market_data.option_chain("NIFTY", exchange="NSE")

if not result:
    st.warning("No data received from API")
    st.stop()

chain = result.chain
spot = chain.at_the_money_strike / 100
atm = int(spot)

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE"))

# 🔥 SAFE FIX (no UI change)
df = df.fillna(0)

df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ==========================================
# CHANGE TRACKING (UNCHANGED)
# ==========================================
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

# ==========================================
# 5. DASHBOARD UI (UNCHANGED)
# ==========================================
max_ce_vol, max_pe_vol = df["volume_CE"].max(), df["volume_PE"].max()
max_ce_oi, max_pe_oi = df["open_interest_CE"].max(), df["open_interest_PE"].max()

# 🔥 SAFE PCR (divide error fix)
total_ce = df["open_interest_CE"].sum()
total_pe = df["open_interest_PE"].sum()
pcr = round(total_pe / total_ce, 2) if total_ce != 0 else 0

st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
m1, m2, m3 = st.columns(3)
m1.metric("SPOT", f"{spot:,.2f}")
m2.metric("PCR", pcr)
m3.metric("STATUS", "📈 NORMAL" if pcr > 0.8 else "📉 BEARISH")

# ==========================================
# SIGNAL PANEL (UNCHANGED)
# ==========================================
st.markdown("---")
st.subheader("🎯 LIVE TRADE SIGNALS")

c1, c2, c3, c4, c5 = st.columns(5)

if is_admin:
    with c1: s_strike = st.text_input("Strike", st.session_state.signal["Strike"])
    with c2: s_entry = st.text_input("Entry", st.session_state.signal["Entry"])
    with c3: s_target = st.text_input("Target", st.session_state.signal["Target"])
    with c4: s_sl = st.text_input("SL", st.session_state.signal["SL"])
    with c5: 
        if st.button("📢 UPDATE"):
            st.session_state.signal = {
                "Strike": s_strike,
                "Entry": s_entry,
                "Target": s_target,
                "SL": s_sl,
                "Status": f"LIVE ({current_admin_name})"
            }
else:
    c1.info(f"STRIKE: {st.session_state.signal['Strike']}")
    c2.success(f"ENTRY: {st.session_state.signal['Entry']}")
    c3.warning(f"TARGET: {st.session_state.signal['Target']}")
    c4.error(f"SL: {st.session_state.signal['SL']}")
    c5.write(f"**STATUS:** {st.session_state.signal['Status']}")

# ==========================================
# 6. OPTION CHAIN (100% SAME UI)
# ==========================================
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], max_ce_oi), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, max_ce_vol), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, max_pe_vol), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], max_pe_oi), axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

def final_style(row):
    styles = [''] * len(row)
    try:
        ce_p = float(str(row.iloc[2]).split('\n')[-1].replace('%',''))
        pe_p = float(str(row.iloc[4]).split('\n')[-1].replace('%',''))

        if ce_p >= 100: styles[2] = 'background-color: #ff5252; color: white; font-weight: bold'
        elif ce_p > 75: styles[2] = 'background-color: #ffcdd2'

        if pe_p >= 100: styles[4] = 'background-color: #2979ff; color: white; font-weight: bold'
        elif pe_p > 75: styles[4] = 'background-color: #bbdefb'

        if row.iloc[3] == atm:
            styles[3] = 'background-color: yellow; color: black; font-weight: bold'

    except:
        pass

    return styles

st.table(ui.style.apply(final_style, axis=1))
