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
st_autorefresh(interval=5000, key="pro_final_v9")

# CSS: Background colors fix karne ke liye
st.markdown("""
    <style>
    /* Metrics clean look */
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    /* Table text center */
    [data-testid="stTable"] td { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATES (For Signals)
# ==========================================
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
    
    # Nifty Change (Assuming 24500 base)
    change_pts = spot - 24500 
    change_pct = (change_pts / 24500) * 100

except Exception as e:
    st.error(f"❌ SDK Error: {e}")
    st.stop()

# ==========================================
# 4. HEADER (Clean Metrics)
# ==========================================
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
m2.metric("INDIA VIX", "13.45") 
m3.metric("VOL SPIKE", "HIGH 🔥" if abs(change_pct) > 0.4 else "NORMAL")
m4.metric("STATUS", "📈 BULLISH" if change_pts > 0 else "📉 BEARISH")

# ==========================================
# 5. ADMIN PANEL (Hamesha Visible)
# ==========================================
st.markdown("---")
with st.container():
    st.subheader("🎯 ADMIN SIGNAL CONTROL")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Input fields
    s_stk = c1.text_input("Strike", st.session_state.signal["Strike"])
    s_ent = c2.text_input("Entry", st.session_state.signal["Entry"])
    s_tgt = c3.text_input("Target", st.session_state.signal["Target"])
    s_sl = c4.text_input("SL", st.session_state.signal["SL"])
    
    if c5.button("📢 UPDATE SIGNAL", use_container_width=True):
        st.session_state.signal = {
            "Strike": s_stk, "Entry": s_ent, 
            "Target": s_tgt, "SL": s_sl, "Status": "LIVE 🔥"
        }
        st.rerun()

# ==========================================
# 6. OPTION CHAIN (OI & VOL % FIXED)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Max calculations for percentages
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

def apply_institutional_style(row):
    # 5 columns mapping
    s = [''] * 5
    try:
        # Extract % values
        c_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        c_vo_p = float(row.iloc[1].split('(')[1].replace('%)',''))
        p_vo_p = float(row.iloc[3].split('(')[1].replace('%)',''))
        p_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))

        # 1. STRIKE (Index 2) - Grey & Yellow ATM
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black'

        # 2. CE SIDE (Blue & Green)
        if c_oi_p > 65: s[0] = 'background-color: #00008B; color: white; font-weight: bold'
        if c_vo_p > 65: s[1] = 'background-color: #006400; color: white; font-weight: bold'

        # 3. PE SIDE (Red & Orange)
        if p_vo_p > 65: s[3] = 'background-color: #8B0000; color: white; font-weight: bold'
        if p_oi_p > 65: s[4] = 'background-color: #FF8C00; color: white; font-weight: bold'

    except: pass
    return s

st.subheader("📊 Institutional Option Chain Analysis")
st.table(ui.style.apply(apply_institutional_style, axis=1))
