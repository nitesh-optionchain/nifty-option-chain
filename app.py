import os, json, streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ==========================================
# 1. SETUP & REFRESH (5 SECONDS)
# ==========================================
st.set_page_config(page_title="NIFTY INSTITUTIONAL PRO", layout="wide")
st_autorefresh(interval=5000, key="nifty_pro_terminal_final")

# Mobile Optimized CSS
st.markdown("""
    <style>
    .main { padding: 0rem 0.5rem; }
    .stMetric { background-color: #1e2130; padding: 12px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stTable"] { overflow-x: auto; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. PERSISTENCE LOGIC (Manual S/R & VIX)
# ==========================================
DB_FILE = "shared_data.json"

def load_shared_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"R": "25000", "S": "24000", "VIX": "13.50"}

def save_shared_data(r, s, v):
    with open(DB_FILE, "w") as f:
        json.dump({"R": r, "S": s, "VIX": v}, f)

# ==========================================
# 3. SDK AUTHENTICATION (With Error Recovery)
# ==========================================
@st.cache_resource
def get_sdk_session():
    try:
        # env_creds=True handles PHONE_NO and MPIN from Secrets
        return InitNubraSdk(NubraEnv.UAT, env_creds=True)
    except Exception as e:
        st.error(f"❌ Login Failed: {e}")
        return None

# Force Reset Button in Sidebar
if st.sidebar.button("🔄 Force Re-login"):
    st.cache_resource.clear()
    st.rerun()

nubra = get_sdk_session()

if nubra:
    try:
        md = MarketData(nubra)
        
        # --- A. OPTION CHAIN DATA ---
        oc_result = md.option_chain("NIFTY", exchange="NSE")
        if not oc_result:
            st.warning("Waiting for Market Data...")
            st.stop()
            
        chain = oc_result.chain
        spot = chain.at_the_money_strike / 100
        atm = int(round(spot / 50) * 50)

        # --- B. HISTORICAL DATA (For Chart) ---
        now = datetime.now()
        chart_req = {
            "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
            "fields": ["open", "high", "low", "close"],
            "startDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "5m", "intraDay": True, "realTime": True
        }
        hist_res = md.historical_data(chart_req)

        # --- C. HEADER METRICS ---
        shared = load_shared_data()
        st.title("🛡️ NIFTY LIVE INSTITUTIONAL DASHBOARD")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("NIFTY SPOT", f"{spot:,.2f}")
        m2.metric("INDIA VIX", shared["VIX"])
        
        # Boring/Trending Logic
        candle_stat = "⌛ FETCHING"
        if hasattr(hist_res, 'data') and hist_res.data:
            df_h = pd.DataFrame(hist_res.data)
            last = df_h.iloc[-1]
            body = abs(last['close'] - last['open'])
            rng = last['high'] - last['low']
            candle_stat = "😴 BORING" if body < (rng * 0.5) else "🚀 TRENDING"
        m3.metric("CANDLE STATUS", candle_stat)
        m4.metric("VOL STATUS", "HIGH 🔥")

        # --- D. INTERACTIVE CHART (Zoomable) ---
        if hasattr(hist_res, 'data') and hist_res.data:
            df_h['time'] = pd.to_datetime(df_h['timestamp'])
            fig = go.Figure(data=[go.Candlestick(
                x=df_h['time'], open=df_h['open'], high=df_h['high'],
                low=df_h['low'], close=df_h['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])
            fig.update_layout(height=400, template='plotly_dark', xaxis_rangeslider_visible=False,
                             margin=dict(l=10, r=10, t=10, b=10), dragmode='pan')
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- E. MANUAL ADMIN PANEL ---
        st.markdown("---")
        st.subheader("⚙️ MANUAL LEVEL UPDATE")
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        new_r = c1.text_input("RESISTANCE (R)", shared["R"])
        new_s = c2.text_input("SUPPORT (S)", shared["S"])
        new_vix = c3.text_input("INDIA VIX", shared["VIX"])
        
        if c4.button("💾 SYNC ALL"):
            save_shared_data(new_r, new_s, new_vix)
            st.success("Synced!")
            st.rerun()
            
        st.info(f"**ACTIVE LEVELS:** Resistance: {new_r} | Support: {new_s}")

        # --- F. OPTION CHAIN WITH COLOURS ---
        df_ce = pd.DataFrame([vars(x) for x in chain.ce])
        df_pe = pd.DataFrame([vars(x) for x in chain.pe])
        df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
        df["STRIKE"] = (df["strike_price"]/100).astype(int)

        max_c_oi = df["open_interest_CE"].max() or 1
        max_c_vo = df["volume_CE"].max() or 1
        max_p_oi = df["open_interest_PE"].max() or 1
        max_p_vo = df["volume_PE"].max() or 1

        def fmt_val(v, m):
            p = (v/m*100) if m > 0 else 0
            return f"{v:,.0f}\n({p:.1f}%)"

        ui = pd.DataFrame()
        ui["CE OI (%)"] = df.apply(lambda r: fmt_val(r["open_interest_CE"], max_c_oi), axis=1)
        ui["CE VOL (%)"] = df.apply(lambda r: fmt_val(r["volume_CE"], max_c_vo), axis=1)
        ui["STRIKE"] = df["STRIKE"]
        ui["PE VOL (%)"] = df.apply(lambda r: fmt_val(r["volume_PE"], max_p_vo), axis=1)
        ui["PE OI (%)"] = df.apply(lambda r: fmt_val(r["open_interest_PE"], max_p_oi), axis=1)

        def institutional_style(row):
            s = [''] * len(row)
            try:
                # Parsing percentages from string
                c_oi_p = float(row.iloc[0].split('(')[1].replace('%)', ''))
                c_vo_p = float(row.iloc[1].split('(')[1].replace('%)', ''))
                p_vo_p = float(row.iloc[3].split('(')[1].replace('%)', ''))
                p_oi_p = float(row.iloc[4].split('(')[1].replace('%)', ''))
                
                raw_c_vo = float(row.iloc[1].split('\n')[0].replace(',', ''))
                raw_p_vo = float(row.iloc[3].split('\n')[0].replace(',', ''))

                # STRIKE & ATM Highlight
                if int(row["STRIKE"]) == atm:
                    s[2] = 'background-color: #FFFF00; color: black; font-weight: bold; text-align: center'
                else:
                    s[2] = 'background-color: #D3D3D3; color: black; text-align: center'

                # CE Side Styles
                if c_oi_p >= 65: s[0] = 'background-color: #00008B; color: white' # Resistance Blue
                if raw_c_vo >= max_c_vo: s[1] = 'background-color: #006400; color: white' # Highest Vol Green
                elif c_vo_p >= 75: s[1] = 'background-color: #FF1493; color: white' # High Vol Pink

                # PE Side Styles
                if raw_p_vo >= max_p_vo: s[3] = 'background-color: #8B0000; color: white' # Highest Vol Red
                elif p_vo_p >= 75: s[3] = 'background-color: #A52A2A; color: white' # High Vol Brown
                if p_oi_p >= 65: s[4] = 'background-color: #FF8C00; color: white' # Support Orange

            except: pass
            return s

        st.table(ui.style.apply(institutional_style, axis=1))

    except Exception as e:
        if "Unauthorized" in str(e):
            st.cache_resource.clear()
            st.warning("Re-authenticating session...")
            st.rerun()
        else:
            st.error(f"Execution Error: {e}")
else:
    st.warning("Please check your PHONE_NO and MPIN in Streamlit Secrets.")
