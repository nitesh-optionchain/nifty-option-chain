import os, json, streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ==========================================
# 1. CONFIG & PERSISTENCE
# ==========================================
st.set_page_config(page_title="NIFTY PRO TERMINAL", layout="wide")
st_autorefresh(interval=5000, key="pro_terminal_fixed")

# File based persistence for S/R Sync
DB_FILE = "shared_levels.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"R": "25000", "S": "24000", "VIX": "13.50"}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

# ==========================================
# 2. SDK LOGIN
# ==========================================
@st.cache_resource
def get_sdk():
    try: return InitNubraSdk(NubraEnv.UAT, env_creds=True)
    except: return None

nubra = get_sdk()
if not nubra:
    st.error("❌ SDK Auth Failed")
    st.stop()

# ==========================================
# 3. DATA FETCHING
# ==========================================
md = MarketData(nubra)
try:
    # Option Chain
    result = md.option_chain("NIFTY", exchange="NSE")
    chain = result.chain
    spot = chain.at_the_money_strike / 100
    atm = int(round(spot / 50) * 50)

    # Historical for Chart
    now = datetime.now()
    chart_req = {
        "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
        "fields": ["open", "high", "low", "close"],
        "startDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "interval": "5m", "intraDay": True, "realTime": True
    }
    hist_res = md.historical_data(chart_req)
except Exception as e:
    st.error(f"API Error: {e}")
    st.stop()

# ==========================================
# 4. HEADER & CHART
# ==========================================
db_data = load_db()
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY SPOT", f"{spot:,.2f}")
m2.metric("INDIA VIX", db_data.get("VIX", "13.50")) # Manual/DB VIX
m3.metric("STATUS", "ACTIVE 🔥")

# Boring Candle Logic
c_stat = "⌛ LOADING"
if hasattr(hist_res, 'data') and hist_res.data:
    df_h = pd.DataFrame(hist_res.data)
    last = df_h.iloc[-1]
    body, rng = abs(last['close'] - last['open']), last['high'] - last['low']
    c_stat = "😴 BORING" if body < (rng * 0.5) else "🚀 TRENDING"
m4.metric("CANDLE", c_stat)

# Interactive Chart (Zoomable)
if hasattr(hist_res, 'data') and hist_res.data:
    df_h['time'] = pd.to_datetime(df_h['timestamp'])
    fig = go.Figure(data=[go.Candlestick(
        x=df_h['time'], open=df_h['open'], high=df_h['high'],
        low=df_h['low'], close=df_h['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    fig.update_layout(height=350, template='plotly_dark', xaxis_rangeslider_visible=False, margin=dict(l=5,r=5,t=5,b=5))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# 5. MANUAL UPDATE PANEL (Admin Sync)
# ==========================================
st.markdown("---")
st.subheader("⚙️ MANUAL UPDATE (S/R & VIX)")
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
new_r = col1.text_input("RESISTANCE (R)", db_data["R"])
new_s = col2.text_input("SUPPORT (S)", db_data["S"])
new_vix = col3.text_input("INDIA VIX", db_data["VIX"])

if col4.button("💾 SYNC ALL"):
    save_db({"R": new_r, "S": new_s, "VIX": new_vix})
    st.rerun()

# Display Current Active Levels
st.info(f"**ACTIVE LEVELS:** Resistance: {new_r} | Support: {new_s} | VIX: {new_vix}")

# ==========================================
# 6. OPTION CHAIN (Color Fixing)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Max values for percentage calculation
max_c_oi = df["open_interest_CE"].max() or 1
max_c_vo = df["volume_CE"].max() or 1
max_p_oi = df["open_interest_PE"].max() or 1
max_p_vo = df["volume_PE"].max() or 1

def fmt(v, m):
    p = (v/m*100) if m > 0 else 0
    return f"{v:,.0f}\n({p:.1f}%)"

ui = pd.DataFrame()
ui["CE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_CE"], max_c_oi), axis=1)
ui["CE VOL (%)"] = df.apply(lambda r: fmt(r["volume_CE"], max_c_vo), axis=1)
ui["STRIKE"] = df["STRIKE"]
ui["PE VOL (%)"] = df.apply(lambda r: fmt(r["volume_PE"], max_p_vo), axis=1)
ui["PE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_PE"], max_p_oi), axis=1)

def apply_institutional_style(row):
    # Strike column is index 2
    s = ['background-color: transparent'] * len(row)
    try:
        # Extract Percentages
        c_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        c_vo_p = float(row.iloc[1].split('(')[1].replace('%)',''))
        p_vo_p = float(row.iloc[3].split('(')[1].replace('%)',''))
        p_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))
        
        raw_c_vo = float(row.iloc[1].split('\n')[0].replace(',',''))
        raw_p_vo = float(row.iloc[3].split('\n')[0].replace(',',''))

        # 1. STRIKE COLUMN (Index 2)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: #FFFF00; color: black; font-weight: bold; text-align: center' # ATM Yellow
        else:
            s[2] = 'background-color: #D3D3D3; color: black; text-align: center' # Strike Grey

        # 2. CE SIDE (Left)
        if c_oi_p >= 65: s[0] = 'background-color: #00008B; color: white' # OI Blue
        if raw_c_vo >= max_c_vo: s[1] = 'background-color: #006400; color: white' # Max Vol Green
        elif c_vo_p >= 70: s[1] = 'background-color: #FF1493; color: white' # High Vol Pink

        # 3. PE SIDE (Right)
        if raw_p_vo >= max_pe_vol: s[3] = 'background-color: #8B0000; color: white' # Max Vol Red
        elif p_vo_p >= 70: s[3] = 'background-color: #A52A2A; color: white' # High Vol Brown
        if p_oi_p >= 65: s[4] = 'background-color: #FF8C00; color: white' # OI Orange

    except: pass
    return s

st.table(ui.style.apply(apply_institutional_style, axis=1))
