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

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth = True

if not st.session_state.is_auth:
    st.title("🛡️ LOGIN")
    uid = st.text_input("Mobile ID", type="password")
    if st.button("LOGIN"):
        if uid in ADMIN_DB:
            st.session_state.is_auth = True
            with open(SESSION_FILE, "w") as f: json.dump({"user_id": uid}, f)
            st.rerun()
    st.stop()

# ================= 2. DATA UTILITIES =================
def normalize_price(value: Any) -> float:
    try:
        price = float(value)
        if abs(price) >= 100000: return price / 100.0
        return price
    except: return np.nan

def response_to_frames(response: Any) -> dict[str, pd.DataFrame]:
    frames = {}
    if not response or not hasattr(response, 'result'): return frames
    for group in response.result:
        for inst_dict in getattr(group, "values", []):
            for symbol, chart in inst_dict.items():
                df = pd.DataFrame({
                    "open": [normalize_price(p.value) for p in chart.open],
                    "high": [normalize_price(p.value) for p in chart.high],
                    "low": [normalize_price(p.value) for p in chart.low],
                    "close": [normalize_price(p.value) for p in chart.close],
                }, index=pd.to_datetime([p.timestamp for p in chart.close], unit='ns', utc=True).tz_convert("Asia/Kolkata"))
                frames[symbol] = df
    return frames

# ================= 3. MARKET SETUP =================
st_autorefresh(interval=10000, key="refresh")
index_choice = st.sidebar.selectbox("Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
market_data = MarketData(st.session_state.nubra)

# ================= 4. MAIN UI =================
res_chain = market_data.option_chain(index_choice, exchange=target_exch)

if res_chain and res_chain.chain:
    chain = res_chain.chain
    # Fix: Get Spot price safely
    raw_spot = getattr(chain, 'underlying_price', 0)
    if raw_spot == 0 and len(chain.ce) > 0:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 0)
    spot = normalize_price(raw_spot)

    st.subheader(f"📈 {index_choice} | Spot: {spot:,.2f}")

    # --- ROW 1: CHART SECTION ---
    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        tab_tv, tab_nubra = st.tabs(["TradingView Chart", "Nubra Live Data"])
        
        with tab_tv:
            # Fix for Apple Chart: Explicitly mapping names
            tv_map = {"NIFTY": "NSE:NIFTY", "BANKNIFTY": "NSE:BANKNIFTY", "SENSEX": "BSE:SENSEX"}
            tv_symbol = tv_map.get(index_choice)
            chart_html = f"""
            <div id="tv_chart" style="height:400px;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
              "width": "100%", "height": 400, "symbol": "{tv_symbol}",
              "interval": "5", "timezone": "Asia/Kolkata", "theme": "light",
              "style": "1", "container_id": "tv_chart", "hide_top_toolbar": true
            }});
            </script>"""
            components.html(chart_html, height=410)

        with tab_nubra:
            try:
                hist = market_data.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open","high","low","close"], "interval": "5m", "intraDay": True})
                df_chart = response_to_frames(hist).get(index_choice, pd.DataFrame())
                if not df_chart.empty:
                    fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'])])
                    fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Loading Nubra Candles...")
            except: st.info("Historical data sync in progress...")

    with col_signal:
        st.markdown("### 🚦 SIGNAL")
        # Logic for a quick signal based on LTP vs ATM
        st.metric("LTP", f"{spot:,.2f}")
        st.info("Scanner Active: Watching for Volume Traps")

    # --- ROW 2: OPTION CHAIN TABLE ---
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)
    
    max_vol_ce = df["volume_CE"].max()
    max_vol_pe = df["volume_PE"].max()
    atm_idx = (df["STRIKE"] - spot).abs().idxmin()
    d_df = df.iloc[max(0, atm_idx-7) : atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI"] = d_df["open_interest_CE"].apply(lambda x: f"{x:,.0f}")
    ui["CE VOL"] = d_df["volume_CE"].apply(lambda x: f"{x:,.0f}")
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL"] = d_df["volume_PE"].apply(lambda x: f"{x:,.0f}")
    ui["PE OI"] = d_df["open_interest_PE"].apply(lambda x: f"{x:,.0f}")

    def style_rows(row):
        styles = [''] * 5
        idx = row.name
        curr_strike = d_df.loc[idx, "STRIKE"]
        v_ce, o_ce = d_df.loc[idx, "volume_CE"], d_df.loc[idx, "open_interest_CE"]
        v_pe, o_pe = d_df.loc[idx, "volume_PE"], d_df.loc[idx, "open_interest_PE"]

        # ATM Highlight
        if abs(curr_strike - spot) < 50: styles[2] = 'background-color: #fff59d; font-weight: bold'
        
        # Purple Trap Logic
        if v_ce > (o_ce * 40): styles[1] = 'background-color: #e1bee7; color: black'
        if v_pe > (o_pe * 40): styles[3] = 'background-color: #e1bee7; color: black'
        
        # Max Volume (Green/Red)
        if v_ce == max_vol_ce: styles[1] = 'background-color: #c8e6c9; color: green'
        if v_pe == max_vol_pe: styles[3] = 'background-color: #ffcdd2; color: red'
        
        return styles

    st.subheader("📊 Trap Scanner (Volume vs OI)")
    st.table(ui.style.apply(style_rows, axis=1))

else:
    st.warning("Connecting to Nubra Market Feed... Please wait.")
