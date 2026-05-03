from __future__ import annotations
import math, os, json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

SESSION_FILE = "session_login.json"
USER_FILE = "authorized_users.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief"})

# Login check (Baar baar logout nahi hoga)
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth = True
        st.session_state.admin_name = ADMIN_DB[saved["user_id"]]

if not st.session_state.is_auth:
    st.title("🛡️ LOGIN")
    uid = st.text_input("Mobile ID", type="password")
    if st.button("LOGIN"):
        if uid in ADMIN_DB:
            st.session_state.is_auth = True
            with open(SESSION_FILE, "w") as f: json.dump({"user_id": uid}, f)
            st.rerun()
    st.stop()

# ================= 2. DATA FETCH & CHARTING =================
st_autorefresh(interval=5000, key="refresh")
index_choice = st.sidebar.selectbox("Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market_data = MarketData(st.session_state.nubra)

# --- Fetching Candle Data for Chart ---
def get_candles(symbol, exch):
    try:
        # 5 minute ki candles fetch kar rahe hain chart ke liye
        res = market_data.historical_data({
            "exchange": exch, "type": "INDEX", "values": [symbol],
            "fields": ["open", "high", "low", "close"],
            "interval": "5m", "intraDay": True
        })
        # Note: Response handling depend karta hai SDK version pe
        # Yahan hum maan ke chal rahe hain ki historical data aa raha hai
        return pd.DataFrame() # Demo ke liye empty, niche logic add kiya hai
    except: return pd.DataFrame()

# ================= 3. MAIN UI =================
res_chain = market_data.option_chain(index_choice, exchange=target_exch)

if res_chain and res_chain.chain:
    chain = res_chain.chain
    raw_spot = getattr(chain.ce[0], 'underlying_price', getattr(chain, 'underlying_price', 0))
    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot

    st.header(f"📈 {index_choice} Live: {spot:,.2f}")

    # --- ROW 1: CANDLE CHART ---
    # Hum TradingView ka widget use karenge jo zyada fast aur smooth hai
    tv_symbol = f"{target_exch}:{index_choice}"
    chart_html = f"""
    <div style="height:400px;">
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "width": "100%", "height": 400, "symbol": "{tv_symbol}",
      "interval": "5", "timezone": "Asia/Kolkata", "theme": "light",
      "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6",
      "enable_publishing": false, "hide_top_toolbar": true, "save_image": false,
      "container_id": "tv_chart"
    }});
    </script>
    <div id="tv_chart"></div>
    </div>
    """
    components.html(chart_html, height=410)

    # --- ROW 2: OPTION CHAIN TABLE (TRAP LOGIC) ---
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)
    
    max_vol_ce = df["volume_CE"].max() or 1
    max_vol_pe = df["volume_PE"].max() or 1
    atm_stk = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    d_df = df.iloc[max(df.index[df["STRIKE"] == atm_stk][0]-7,0) : df.index[df["STRIKE"] == atm_stk][0]+8]

    ui = pd.DataFrame()
    ui["CE OI"] = d_df.apply(lambda r: f"{r['open_interest_CE']:,.0f}", axis=1)
    ui["CE VOL"] = d_df.apply(lambda r: f"{r['volume_CE']:,.0f}", axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL"] = d_df.apply(lambda r: f"{r['volume_PE']:,.0f}", axis=1)
    ui["PE OI"] = d_df.apply(lambda r: f"{r['open_interest_PE']:,.0f}", axis=1)

    def style_table(row):
        s = [''] * 5
        idx = row.name
        cur = int(d_df.loc[idx, "STRIKE"])
        vol_ce, oi_ce = d_df.loc[idx, "volume_CE"], d_df.loc[idx, "open_interest_CE"]
        vol_pe, oi_pe = d_df.loc[idx, "volume_PE"], d_df.loc[idx, "open_interest_PE"]

        if cur == int(atm_stk): s[2] = 'background-color:yellow; font-weight:bold'
        else: s[2] = 'background-color:#f0f2f6'

        # Trap Detection (Purple)
        if vol_ce > (oi_ce * 40): s[1] = 'background-color:#e1bee7; font-weight:bold'
        elif vol_ce == max_vol_ce: s[1] = 'background-color:#1b5e20; color:white'

        if vol_pe > (oi_pe * 40): s[3] = 'background-color:#e1bee7; font-weight:bold'
        elif vol_pe == max_vol_pe: s[3] = 'background-color:#b71c1c; color:white'
        
        return s

    st.subheader("📊 Option Chain & Trap Scanner")
    st.table(ui.style.apply(style_table, axis=1))

else:
    st.info("Connecting to Market Data...")
