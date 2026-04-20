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
st_autorefresh(interval=5000, key="pro_final_v4")

# ==========================================
# 2. PERSISTENCE (S/R & VIX)
# ==========================================
DB_FILE = "shared_levels.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"R": "25000", "S": "24000", "VIX": "13.50"}

def save_db(r, s, v):
    with open(DB_FILE, "w") as f: json.dump({"R": r, "S": s, "VIX": v}, f)

# ==========================================
# 3. SDK LOGIN & DATA FETCH
# ==========================================
@st.cache_resource
def get_sdk():
    try: return InitNubraSdk(NubraEnv.UAT, env_creds=True)
    except: return None

nubra = get_sdk()
if not nubra:
    st.error("❌ SDK Auth Failed")
    st.stop()

md = MarketData(nubra)

try:
    # Option Chain Data
    result = md.option_chain("NIFTY", exchange="NSE")
    chain = result.chain
    spot = chain.at_the_money_strike / 100
    atm = int(round(spot / 50) * 50)
    
    # Nifty Change Logic (Assuming 24500 as prev close for demo, update with real prev_close)
    prev_close = 24500 
    change = spot - prev_close
    change_pct = (change / prev_close) * 100

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
    if "Unauthorized" in str(e):
        st.cache_resource.clear()
        st.rerun()
    st.error(f"API Error: {e}")
    st.stop()

# ==========================================
# 4. UPPER HEADER (Live Nifty, VIX, Vol Spike)
# ==========================================
db_data = load_db()
st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")

m1, m2, m3, m4 = st.columns(4)
# Nifty Position (Kitna bada ya gira)
m1.metric("NIFTY SPOT", f"{spot:,.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
# India VIX from Manual Update
m2.metric("INDIA VIX", db_data["VIX"])
# Volume Spike Logic
m3.metric("VOLUME SPIKE", "HIGH 🔥" if change_pct > 0.5 or change_pct < -0.5 else "NORMAL")
# Status
m4.metric("MARKET STATUS", "BULLISH 🚀" if change > 0 else "BEARISH 📉")

# --- CHART ---
if hasattr(hist_res, 'data') and hist_res.data:
    df_h = pd.DataFrame(hist_res.data)
    df_h['time'] = pd.to_datetime(df_h['timestamp'])
    fig = go.Figure(data=[go.Candlestick(
        x=df_h['time'], open=df_h['open'], high=df_h['high'],
        low=df_h['low'], close=df_h['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    fig.update_layout(height=350, template='plotly_dark', xaxis_rangeslider_visible=False, margin=dict(l=5,r=5,t=5,b=5))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# 5. ADMIN MANUAL UPDATE (S/R & VIX)
# ==========================================
st.markdown("---")
with st.expander("⚙️ ADMIN CONTROL: UPDATE S/R & VIX"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    new_r = c1.text_input("RESISTANCE (R)", db_data["R"])
    new_s = c2.text_input("SUPPORT (S)", db_data["S"])
    new_vix = c3.text_input("INDIA VIX", db_data["VIX"])
    if c4.button("SYNC"):
        save_db(new_r, new_s, new_vix)
        st.rerun()

# ==========================================
# 6. OPTION CHAIN (OI Color & Strike Color)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

max_c_oi = df["open_interest_CE"].max() or 1
max_p_oi = df["open_interest_PE"].max() or 1

def fmt(v, m):
    p = (v/m*100) if m > 0 else 0
    return f"{v:,.0f}\n({p:.1f}%)"

ui = pd.DataFrame()
ui["CE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_CE"], max_c_oi), axis=1)
ui["CE VOL"] = df["volume_CE"].apply(lambda x: f"{x:,.0f}")
ui["STRIKE"] = df["STRIKE"]
ui["PE VOL"] = df["volume_PE"].apply(lambda x: f"{x:,.0f}")
ui["PE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_PE"], max_p_oi), axis=1)

def apply_custom_style(row):
    s = [''] * len(row)
    try:
        # Extract Percentage from string "(65.0%)"
        ce_oi_p = float(row.iloc[0].split('(')[1].replace('%)',''))
        pe_oi_p = float(row.iloc[4].split('(')[1].replace('%)',''))

        # 1. STRIKE COLUMN (Light Grey)
        if int(row["STRIKE"]) == atm:
            s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else:
            s[2] = 'background-color: #D3D3D3; color: black' # Light Grey

        # 2. OI COLOUR (65% se jada hone par)
        if ce_oi_p > 65:
            s[0] = 'background-color: #00008B; color: white' # Deep Blue for CE
        
        if pe_oi_p > 65:
            s[4] = 'background-color: #FF8C00; color: white' # Deep Orange for PE

    except: pass
    return s

st.table(ui.style.apply(apply_custom_style, axis=1))
