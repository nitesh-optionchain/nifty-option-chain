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
st_autorefresh(interval=5000, key="pro_final_v6")

# ==========================================
# 2. ADMIN AUTH (Aapka Original Logic)
# ==========================================
ADMIN_DB = {"9304768496": "Admin Chief", "9822334455": "Amit Kumar"}
url_id = st.query_params.get("id", None)
is_admin = url_id in ADMIN_DB

if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}

# ==========================================
# 3. SDK LOGIN & DATA
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
    
    # Live Nifty Change (Demo prev close: 24500)
    change_pts = spot - 24500 
    change_pct = (change_pts / 24500) * 100

except Exception as e:
    st.error(f"❌ SDK Error: {e}")
    st.stop()

# ==========================================
# 4. HEADER (Nifty Change, VIX, Spike)
# ==========================================
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
m2.metric("INDIA VIX", "13.45") 
m3.metric("VOL SPIKE", "HIGH 🔥" if abs(change_pct) > 0.4 else "NORMAL")
m4.metric("STATUS", "📈 BULLISH" if change_pts > 0 else "📉 BEARISH")

# ==========================================
# 5. ADMIN SIGNALS
# ==========================================
st.markdown("---")
st.subheader("🎯 LIVE TRADE SIGNALS")
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
# 6. OPTION CHAIN (OI & VOL % UPGRADE)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Max values for % calculation
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
ui["CE VOL (%)"] = display_df.apply(lambda r: fmt(r["volume_CE"], max_c_vo), axis=1) # Fixed Vol %
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL (%)"] = display_df.apply(lambda r: fmt(r["volume_PE"], max_p_vo), axis=1) # Fixed Vol %
ui["PE OI (%)"] = display_df.apply(lambda r: fmt(r["open_interest_PE"], max_p_oi), axis=1)

def apply_final_style(row):
    s = [''] * len(row)
    try:
        # Extract Percentages from all columns
        c_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        c_vo_p = float(row.iloc[1].split('(')[1].replace('%)',''))
        p_vo_p = float(row.iloc[3].split('(')[1].replace('%)',''))
        p_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))

        # 1. STRIKE COLUMN (Light Grey & Yellow ATM)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black'

        # 2. CE SIDE COLOURS (65% Rule)
        if c_oi_p > 65: s[0] = 'background-color: #00008B; color: white' # Deep Blue OI
        if c_vo_p > 65: s[1] = 'background-color: #006400; color: white' # Deep Green Vol

        # 3. PE SIDE COLOURS (65% Rule)
        if p_vo_p > 65: s[3] = 'background-color: #8B0000; color: white' # Deep Red Vol
        if p_oi_p > 65: s[4] = 'background-color: #FF8C00; color: white' # Deep Orange OI

    except: pass
    return s

st.subheader("📊 Institutional Option Chain (OI & VOL %)")
st.table(ui.style.apply(apply_final_style, axis=1))
