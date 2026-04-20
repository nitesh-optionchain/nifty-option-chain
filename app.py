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
st_autorefresh(interval=5000, key="pro_final_v10")

# CSS: Background colors aur CE OI Blue fix karne ke liye
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    [data-testid="stTable"] td { text-align: center !important; }
    /* Force CE OI Blue */
    .ce-oi-blue { background-color: #00008B !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATES
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
    
    if result and result.chain:
        chain = result.chain
        spot = chain.at_the_money_strike / 100
        atm = int(round(spot / 50) * 50)
        
        # Nifty Change Logic (Real data se close na mile toh spot hi base hai)
        # Yahan hum 24800 dummy le rahe hain, ise aap live close se replace kar sakte hain
        prev_close = 24800 
        change_pts = spot - prev_close
        change_pct = (change_pts / prev_close) * 100
    else:
        st.error("Waiting for API Data...")
        st.stop()

except Exception as e:
    st.error(f"❌ SDK Error: {e}")
    st.stop()

# ==========================================
# 4. HEADER (Nifty Spot, VIX, Spike - FIXED)
# ==========================================
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
m1, m2, m3, m4 = st.columns(4)

# Spot aur Change hamesha show hoga agar data hai
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
m2.metric("INDIA VIX", "13.45") # Manual for now
m3.metric("VOL SPIKE", "HIGH 🔥" if abs(change_pct) > 0.4 else "NORMAL")
m4.metric("STATUS", "📈 BULLISH" if change_pts > 0 else "📉 BEARISH")

# ==========================================
# 5. ADMIN PANEL (Visible)
# ==========================================
st.markdown("---")
with st.container():
    st.subheader("🎯 ADMIN SIGNAL CONTROL")
    c1, c2, c3, c4, c5 = st.columns(5)
    s_stk = c1.text_input("Strike", st.session_state.signal["Strike"])
    s_ent = c2.text_input("Entry", st.session_state.signal["Entry"])
    s_tgt = c3.text_input("Target", st.session_state.signal["Target"])
    s_sl = c4.text_input("SL", st.session_state.signal["SL"])
    if c5.button("📢 UPDATE", use_container_width=True):
        st.session_state.signal = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl, "Status": "LIVE 🔥"}
        st.rerun()

# ==========================================
# 6. OPTION CHAIN (OI & VOL % FIXED)
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

def apply_institutional_style(row):
    s = [''] * 5
    try:
        c_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        c_vo_p = float(row.iloc[1].split('(')[1].replace('%)',''))
        p_vo_p = float(row.iloc[3].split('(')[1].replace('%)',''))
        p_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))

        # STRIKE COLOR (Grey / Yellow)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black'

        # CE SIDE (Blue & Green)
        if c_oi_p > 65: s[0] = 'background-color: #00008B !important; color: white !important' 
        if c_vo_p > 65: s[1] = 'background-color: #006400 !important; color: white !important'

        # PE SIDE (Red & Orange)
        if p_vo_p > 65: s[3] = 'background-color: #8B0000 !important; color: white !important'
        if p_oi_p > 65: s[4] = 'background-color: #FF8C00 !important; color: white !important'
    except: pass
    return s

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(apply_institutional_style, axis=1))
