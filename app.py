import os, json, streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ==========================================
# 1. CONFIG & REFRESH
# ==========================================
st.set_page_config(page_title="NIFTY PRO - ADMIN PANEL", layout="wide")
st_autorefresh(interval=5000, key="pro_final_v7")

# Global CSS for Table & Metrics
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #444; }
    [data-testid="stTable"] td { text-align: center !important; vertical-align: middle !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. ADMIN AUTH & SIGNALS (DASHBOARD PAR FIX)
# ==========================================
ADMIN_DB = {"9304768496": "Admin Chief", "7982046438": "Rupesh Kumar"}
url_id = st.query_params.get("id", None)
is_admin = url_id in ADMIN_DB

if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}

# ==========================================
# 3. SDK LOGIN & DATA FETCH
# ==========================================
try:
    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
    
    nubra = st.session_state.nubra
    market_data = MarketData(nubra)
    
    result = market_data.option_chain("NIFTY", exchange="NSE")
    chain = result.chain
    spot = chain.at_the_money_strike / 100
    atm = int(round(spot / 50) * 50)
    
    # Nifty Change Calculation (Assuming 24500 base)
    change_pts = spot - 24500 
    change_pct = (change_pts / 24500) * 100

except Exception as e:
    st.error(f"❌ SDK Error: {e}")
    st.stop()

# ==========================================
# 4. HEADER (Nifty Spot, VIX, Spike)
# ==========================================
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
m2.metric("INDIA VIX", "13.45") 
m3.metric("VOL SPIKE", "HIGH 🔥" if abs(change_pct) > 0.4 else "NORMAL")
m4.metric("STATUS", "📈 BULLISH" if change_pts > 0 else "📉 BEARISH")

# ==========================================
# 5. ADMIN PANEL (DASHBOARD PAR VISIBLE)
# ==========================================
st.markdown("---")
st.subheader("🎯 LIVE TRADE SIGNALS (ADMIN PANEL)")
s1, s2, s3, s4, s5 = st.columns(5)

if is_admin:
    with s1: ss_strike = st.text_input("Strike", st.session_state.signal["Strike"])
    with s2: ss_entry = st.text_input("Entry", st.session_state.signal["Entry"])
    with s3: ss_target = st.text_input("Target", st.session_state.signal["Target"])
    with s4: ss_sl = st.text_input("SL", st.session_state.signal["SL"])
    if s5.button("📢 UPDATE"):
        st.session_state.signal = {"Strike": ss_strike, "Entry": ss_entry, "Target": ss_target, "SL": ss_sl, "Status": "LIVE"}
        st.rerun()
else:
    s1.info(f"STRIKE: {st.session_state.signal['Strike']}")
    s2.success(f"ENTRY: {st.session_state.signal['Entry']}")
    s3.warning(f"TARGET: {st.session_state.signal['Target']}")
    s4.error(f"SL: {st.session_state.signal['SL']}")
    s5.write(f"**STATUS:** {st.session_state.signal['Status']}")

# ==========================================
# 6. OPTION CHAIN (OI & VOL % FIXED COLOURS)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

max_c_oi = df["open_interest_CE"].max() or 1
max_p_oi = df["open_interest_PE"].max() or 1
max_c_vo = df["volume_CE"].max() or 1
max_p_vo = df["volume_PE"].max() or 1

def fmt(v, m):
    p = (v/m*100) if m > 0 else 0
    return f"{v:,.0f}\n({p:.1f}%)"

atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-8,0): atm_idx+9].copy()

ui = pd.DataFrame()
ui["CE OI (%)"] = display_df.apply(lambda r: fmt(r["open_interest_CE"], max_c_oi), axis=1)
ui["CE VOL (%)"] = display_df.apply(lambda r: fmt(r["volume_CE"], max_c_vo), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL (%)"] = display_df.apply(lambda r: fmt(r["volume_PE"], max_p_vo), axis=1)
ui["PE OI (%)"] = display_df.apply(lambda r: fmt(r["open_interest_PE"], max_p_oi), axis=1)

def apply_final_style(row):
    # s list length must match ui columns (5 columns)
    s = ['background-color: transparent'] * 5
    try:
        # Index based mapping
        c_oi_val = float(row.iloc[0].split('(')[1].replace('%)',''))
        c_vo_val = float(row.iloc[1].split('(')[1].replace('%)',''))
        p_vo_val = float(row.iloc[3].split('(')[1].replace('%)',''))
        p_oi_val = float(row.iloc[4].split('(')[1].replace('%)',''))

        # STRIKE (Index 2)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black'

        # CE SIDE (Index 0, 1)
        if c_oi_val > 65: 
            s[0] = 'background-color: #00008B !important; color: white !important' # Deep Blue
        if c_vo_val > 65: 
            s[1] = 'background-color: #006400 !important; color: white !important' # Deep Green

        # PE SIDE (Index 3, 4)
        if p_vo_val > 65: 
            s[3] = 'background-color: #8B0000 !important; color: white !important' # Deep Red
        if p_oi_val > 65: 
            s[4] = 'background-color: #FF8C00 !important; color: white !important' # Deep Orange

    except: pass
    return s

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(apply_final_style, axis=1))
