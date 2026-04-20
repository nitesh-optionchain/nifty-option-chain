import os, json, streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ==========================================
# 1. CONFIG & REFRESH (Fixed for Mobile & Admin)
# ==========================================
st.set_page_config(page_title="NIFTY PRO - INSTITUTIONAL", layout="wide")
st_autorefresh(interval=5000, key="pro_terminal_final")

# CSS for better visibility
st.markdown("<style>.stMetric { background-color: #1e2130; padding: 12px; border-radius: 10px; border: 1px solid #333; }</style>", unsafe_allow_html=True)

# ==========================================
# 2. ADMIN AUTH (Your Logic)
# ==========================================
ADMIN_DB = {"9304768496": "Admin Chief", "9822334455": "Amit Kumar"}
url_id = st.query_params.get("id", None)
is_admin = url_id in ADMIN_DB or st.sidebar.text_input("Admin ID:", type="password") in ADMIN_DB

# ==========================================
# 3. SDK & DATA FETCH (Safe Integration)
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
    # Option Chain for Table
    oc_result = md.option_chain("NIFTY", exchange="NSE")
    chain = oc_result.chain
    spot = chain.at_the_money_strike / 100
    atm = int(round(spot / 50) * 50)

    # Historical for Chart & Boring Candle (Your Request)
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
    st.error(f"Data Error: {e}")
    st.stop()

# ==========================================
# 4. DASHBOARD HEADER & CHART (Zoom Enabled)
# ==========================================
st.title("🛡️ NIFTY LIVE TERMINAL")

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY SPOT", f"{spot:,.2f}")
m2.metric("INDIA VIX", "13.45") # Hardcoded or fetch from SDK

# Boring Candle Logic
status = "⌛ LOADING"
if hasattr(hist_res, 'data') and hist_res.data:
    df_h = pd.DataFrame(hist_res.data)
    last = df_h.iloc[-1]
    body, rng = abs(last['close'] - last['open']), last['high'] - last['low']
    status = "😴 BORING" if body < (rng * 0.5) else "🚀 TRENDING"
m3.metric("CANDLE", status)
m4.metric("PCR", "0.92") # Calculate if needed

# --- INTERACTIVE CHART ---
if hasattr(hist_res, 'data') and hist_res.data:
    df_h['time'] = pd.to_datetime(df_h['timestamp'])
    fig = go.Figure(data=[go.Candlestick(
        x=df_h['time'], open=df_h['open'], high=df_h['high'],
        low=df_h['low'], close=df_h['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    fig.update_layout(height=400, template='plotly_dark', xaxis_rangeslider_visible=False, dragmode='pan')
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# 5. SIGNAL PANEL (Your Admin Logic)
# ==========================================
st.markdown("---")
if "sig" not in st.session_state: st.session_state.sig = {"S": "-", "E": "-", "T": "-", "SL": "-", "St": "WAITING"}

c1, c2, c3, c4, c5 = st.columns(5)
if is_admin:
    s_s = c1.text_input("Strike", st.session_state.sig["S"])
    s_e = c2.text_input("Entry", st.session_state.sig["E"])
    s_t = c3.text_input("Target", st.session_state.sig["T"])
    s_sl = c4.text_input("SL", st.session_state.sig["SL"])
    if c5.button("📢 UPDATE"):
        st.session_state.sig = {"S": s_s, "E": s_e, "T": s_t, "SL": s_sl, "St": "LIVE"}
        st.rerun()
else:
    c1.metric("STRIKE", st.session_state.sig["S"])
    c2.metric("ENTRY", st.session_state.sig["E"])
    c3.metric("TARGET", st.session_state.sig["T"])
    c4.metric("SL", st.session_state.sig["SL"])
    c5.write(f"**STATUS:** {st.session_state.sig['St']}")

# ==========================================
# 6. OPTION CHAIN (Merge Buildup + Inst. Colors)
# ==========================================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

max_c_oi, max_c_vo = df["open_interest_CE"].max() or 1, df["volume_CE"].max() or 1
max_p_oi, max_p_vo = df["open_interest_PE"].max() or 1, df["volume_PE"].max() or 1

def fmt(v, m):
    p = (v/m*100) if m > 0 else 0
    return f"{v:,.0f}\n{p:.1f}%"

ui = pd.DataFrame()
ui["CE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_CE"], max_c_oi), axis=1)
ui["CE VOL (%)"] = df.apply(lambda r: fmt(r["volume_CE"], max_c_vo), axis=1)
ui["STRIKE"] = df["STRIKE"]
ui["PE VOL (%)"] = df.apply(lambda r: fmt(r["volume_PE"], max_p_vo), axis=1)
ui["PE OI (%)"] = df.apply(lambda r: fmt(r["open_interest_PE"], max_p_oi), axis=1)

def final_style(row):
    s = [''] * len(row)
    try:
        c_oi_p = float(row.iloc[0].split('\n')[1].replace('%',''))
        c_vo_p = float(row.iloc[1].split('\n')[1].replace('%',''))
        p_vo_p = float(row.iloc[3].split('\n')[1].replace('%',''))
        p_oi_p = float(row.iloc[4].split('\n')[1].replace('%',''))

        # Strike / ATM
        if int(row["STRIKE"]) == atm: s[2] = 'background-color: yellow; color: black; font-weight: bold'
        else: s[2] = 'background-color: #D3D3D3; color: black'

        # Institutional Buildup Colors
        if c_oi_p >= 65: s[0] = 'background-color: #00008B; color: white' # Resistance
        if c_vo_p >= 90: s[1] = 'background-color: #006400; color: white' # High Volume
        if p_oi_p >= 65: s[4] = 'background-color: #FF8C00; color: white' # Support
        if p_vo_p >= 90: s[3] = 'background-color: #8B0000; color: white' # High Volume
    except: pass
    return s

st.table(ui.style.apply(final_style, axis=1))
