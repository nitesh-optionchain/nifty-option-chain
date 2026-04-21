from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# ==========================================
# ADMIN LOGIN
# ==========================================
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
        user_key = st.text_input("Enter ID", type="password")
        if user_key in ADMIN_DB:
            is_admin = True
            current_admin_name = ADMIN_DB[user_key]
            st.sidebar.success(f"✅ {current_admin_name}")

# ==========================================
# SESSION STATE
# ==========================================
if "prev_df" not in st.session_state: st.session_state.prev_df = None
if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}
if "sr" not in st.session_state:
    st.session_state.sr = {"support": "-", "resistance": "-"}

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

# ===== LIVE NIFTY FIX =====
spot = getattr(chain, "underlying_value", None)
if not spot:
    spot = chain.at_the_money_strike / 100

prev_close = getattr(chain, "previous_close", None)

if prev_close:
    change = round(spot - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2)
    nifty_text = f"{spot:,.2f} ({change:+} | {change_pct:+}%)"
    color = "#00ff00" if change > 0 else "#ff5252"
else:
    nifty_text = f"{spot:,.2f}"
    color = "#00ffcc"

# ===== VIX =====
vix = getattr(chain, "vix", "N/A")

# ==========================================
# UI HEADER
# ==========================================
st.title("🛡️ SMART WEALTH AI 5")

st.markdown(
    f"""
    <div style="background:#111;padding:15px;border-radius:10px;text-align:center">
        <h2 style="color:white;">📊 NIFTY LIVE</h2>
        <h1 style="color:{color};">{nifty_text}</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# ==========================================
# METRICS
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

max_ce_vol = df["volume_CE"].max()
max_pe_vol = df["volume_PE"].max()
max_ce_oi = df["open_interest_CE"].max()
max_pe_oi = df["open_interest_PE"].max()

total_ce = df["open_interest_CE"].sum()
total_pe = df["open_interest_PE"].sum()
pcr = round(total_pe / total_ce, 2) if total_ce else 0

m1, m2, m3 = st.columns(3)
m1.metric("PCR", pcr)
m2.metric("VIX", vix)
m3.metric("STATUS", "📈 NORMAL" if pcr > 0.8 else "📉 BEARISH")

# ==========================================
# ADMIN SIGNAL
# ==========================================
st.subheader("🎯 TRADE SIGNAL")

c1,c2,c3,c4,c5 = st.columns(5)

if is_admin:
    s1 = c1.text_input("Strike", st.session_state.signal["Strike"])
    s2 = c2.text_input("Entry", st.session_state.signal["Entry"])
    s3 = c3.text_input("Target", st.session_state.signal["Target"])
    s4 = c4.text_input("SL", st.session_state.signal["SL"])

    if c5.button("UPDATE"):
        st.session_state.signal = {
            "Strike": s1,
            "Entry": s2,
            "Target": s3,
            "SL": s4,
            "Status": f"LIVE ({current_admin_name})"
        }
else:
    c1.info(st.session_state.signal["Strike"])
    c2.success(st.session_state.signal["Entry"])
    c3.warning(st.session_state.signal["Target"])
    c4.error(st.session_state.signal["SL"])
    c5.write(st.session_state.signal["Status"])

# ==========================================
# SUPPORT / RESISTANCE
# ==========================================
st.subheader("📊 SUPPORT / RESISTANCE")

s1,s2,s3 = st.columns(3)

if is_admin:
    sup = s1.text_input("Support", st.session_state.sr["support"])
    res = s2.text_input("Resistance", st.session_state.sr["resistance"])

    if s3.button("SET"):
        st.session_state.sr = {"support": sup, "resistance": res}

a,b = st.columns(2)
a.metric("🟢 SUPPORT", st.session_state.sr["support"])
b.metric("🔴 RESISTANCE", st.session_state.sr["resistance"])

# ==========================================
# OPTION CHAIN (UNCHANGED)
# ==========================================
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8]

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["last_traded_price_CE"], r["open_interest_CE"]), axis=1)
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], 0, max_ce_oi), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, max_ce_vol), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, max_pe_vol), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], 0, max_pe_oi), axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["last_traded_price_PE"], r["open_interest_PE"]), axis=1)

def style(row):
    styles = ['']*len(row)
    if row.iloc[3] == atm:
        styles[3] = 'background-color:yellow;color:black;font-weight:bold'
    return styles

st.table(ui.style.apply(style, axis=1))
