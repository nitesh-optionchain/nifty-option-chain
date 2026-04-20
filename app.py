import os, json, streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ==========================================
# 1. CONFIG & REFRESH
# ==========================================
st.set_page_config(page_title="NIFTY PRO - ADMIN PANEL", layout="wide")
st_autorefresh(interval=5000, key="pro_final_v5")

# Persistence for Manual S/R & VIX (Since SDK doesn't give VIX directly)
DB_FILE = "shared_levels.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"R": "25000", "S": "24000", "VIX": "13.50"}

def save_db(r, s, v):
    with open(DB_FILE, "w") as f: json.dump({"R": r, "S": s, "VIX": v}, f)

# ==========================================
# 2. ADMIN & AUTH (Aapka logic)
# ==========================================
ADMIN_DB = {"9304768496": "Admin Chief", "7982046438": "Amit Kumar"}
url_id = st.query_params.get("id", None)
is_admin = url_id in ADMIN_DB

# ==========================================
# 3. SDK LOGIN & DATA FETCH
# ==========================================
try:
    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
    
    nubra = st.session_state.nubra
    market_data = MarketData(nubra)
    
    # Data Fetch
    result = market_data.option_chain("NIFTY", exchange="NSE")
    chain = result.chain
    spot = chain.at_the_money_strike / 100
    atm = int(round(spot / 50) * 50)
    
    # Live Change Logic (Assuming 24500 as prev close - update with actual if available)
    prev_close = 24500 
    change_pts = spot - prev_close
    change_pct = (change_pts / prev_close) * 100

except Exception as e:
    st.error(f"❌ SDK Auth Failed: {e}")
    st.stop()

# ==========================================
# 4. DASHBOARD HEADER (UPGRADED)
# ==========================================
db_data = load_db()
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")

m1, m2, m3, m4 = st.columns(4)
# 🔥 LIVE NIFTY WITH CHANGE
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
# 🔥 INDIA VIX (Manual/DB)
m2.metric("INDIA VIX", db_data["VIX"])
# 🔥 VOL SPIKE LOGIC
m3.metric("VOL SPIKE", "HIGH 🔥" if abs(change_pct) > 0.4 else "NORMAL")
m4.metric("STATUS", "📈 BULLISH" if change_pts > 0 else "📉 BEARISH")

# ==========================================
# 5. ADMIN CONTROL & SIGNALS
# ==========================================
if "signal" not in st.session_state:
    st.session_state.signal = {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"}

st.markdown("---")
with st.expander("🛠️ ADMIN CONTROL PANEL"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    new_r = c1.text_input("RESISTANCE (R)", db_data["R"])
    new_s = c2.text_input("SUPPORT (S)", db_data["S"])
    new_vix = c3.text_input("INDIA VIX", db_data["VIX"])
    if c4.button("💾 SYNC ALL"):
        save_db(new_r, new_s, new_vix)
        st.rerun()

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
# 6. OPTION CHAIN (UPGRADED STYLING)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

max_c_oi = df["open_interest_CE"].max() or 1
max_p_oi = df["open_interest_PE"].max() or 1

def format_ui(val, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({p:.1f}%)"

atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-8,0): atm_idx+9].copy()

ui = pd.DataFrame()
ui["CE OI (%)"] = display_df.apply(lambda r: format_ui(r["open_interest_CE"], max_c_oi), axis=1)
ui["CE VOL"] = display_df["volume_CE"].map(lambda x: f"{x:,.0f}")
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL"] = display_df["volume_PE"].map(lambda x: f"{x:,.0f}")
ui["PE OI (%)"] = display_df.apply(lambda r: format_ui(r["open_interest_PE"], max_p_oi), axis=1)

def apply_institutional_style(row):
    s = [''] * len(row)
    try:
        # Extract % values from string
        c_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        p_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))

        # 1. STRIKE COLUMN (Light Grey & Yellow ATM)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black'

        # 2. OI COLOUR UPGRADE (65% Rule)
        if c_oi_p > 65:
            s[0] = 'background-color: #00008B; color: white' # Deep Blue (CE Resistance)
        
        if p_oi_p > 65:
            s[4] = 'background-color: #FF8C00; color: white' # Deep Orange (PE Support)

    except: pass
    return s

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(apply_institutional_style, axis=1))
