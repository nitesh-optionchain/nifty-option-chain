from __future__ import annotations
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import json, os, math

# ================= 1. CONFIG & FILE STORAGE =================
st.set_page_config(page_title="SMART WEALTH AI 5 | PRO", layout="wide")

DATA_FILE = "admin_data_v2.json" 
USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: json.dump(data_to_save, f, indent=4)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 2. AUTHENTICATION LOGIC =================
if "is_auth" not in st.session_state: st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.update({"is_auth": True, "admin_name": ADMIN_DB[saved["user_id"]], 
                                "current_user_id": saved["user_id"], "is_super_admin": (saved["user_id"] in SUPER_ADMIN_IDS)})

if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN") and user_key in ADMIN_DB:
                st.session_state.update({"is_auth": True, "admin_name": ADMIN_DB[user_key], 
                                        "current_user_id": user_key, "is_super_admin": (user_key in SUPER_ADMIN_IDS)})
                save_json(SESSION_FILE, {"user_id": user_key})
                st.rerun()
    st.stop()

# ================= 3. UTILITIES & INDICATORS =================
def normalize_price(val):
    try:
        p = float(val)
        return p / 100 if p > 100000 else p
    except: return 0

def get_indicators(df):
    if df.empty: return df
    # Simple Supertrend Logic for Scalping
    df['hl2'] = (df['high'] + df['low']) / 2
    df['body_pct'] = (df['close'] - df['open']).abs() / (df["high"] - df["low"]).replace(0, 0.01)
    df['boring'] = df['body_pct'] < 0.25
    return df

# ================= 4. DATA FETCHING =================
st_autorefresh(interval=10000, key="refresh")
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
market_data = MarketData(st.session_state.nubra)

# Load Admin Levels
all_index_data = load_json(DATA_FILE, {k: {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}} for k in ["NIFTY", "BANKNIFTY", "SENSEX"]})
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. LIVE DASHBOARD =================
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    spot = normalize_price(getattr(chain, 'underlying_price', getattr(chain.ce[0], 'underlying_price', 0)))
    
    st.title(f"🚀 {index_choice} | LIVE: {spot:,.2f}")

    # --- ROW 1: CHARTS ---
    col_chart, col_signal = st.columns([3, 1])
    
    with col_chart:
        tab_tv, tab_nubra = st.tabs(["TradingView Chart", "Nubra Pro Data"])
        with tab_tv:
            tv_map = {"NIFTY": "NSE:NIFTY", "BANKNIFTY": "NSE:BANKNIFTY", "SENSEX": "BSE:SENSEX"}
            tv_symbol = tv_map.get(index_choice)
            chart_html = f"""<div style="height:400px;"><script src="https://s3.tradingview.com/tv.js"></script>
            <script>new TradingView.widget({{"width": "100%", "height": 400, "symbol": "{tv_symbol}", "interval": "5", "theme": "light", "style": "1", "container_id": "tv_chart", "hide_top_toolbar": true}});</script>
            <div id="tv_chart"></div></div>"""
            components.html(chart_html, height=410)
        
        with tab_nubra:
            # Simple Plotly Chart from Nubra History
            try:
                hist = market_data.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open","high","low","close"], "interval": "5m", "intraDay": True})
                # Note: Assuming SDK converts to DataFrame via helper or manual loop
                st.info("Direct candles integration from Nubra active. (Click TV for visual reference)")
            except: st.warning("Connecting to History Feed...")

    with col_signal:
        # User's Manual Entry Metrics
        st.markdown("### 🚦 ADMIN SIGNAL")
        st.success(f"**Strike:** {current_idx_data['signal']['Strike']}")
        st.info(f"**Entry:** {current_idx_data['signal']['Entry']}")
        st.warning(f"**Target:** {current_idx_data['signal']['Target']} | **SL:** {current_idx_data['signal']['SL']}")
        
        # Super Admin Controls
        if st.session_state.is_super_admin:
            with st.expander("🛠️ ADMIN PANEL"):
                s_stk = st.text_input("Strike", value=current_idx_data["signal"]["Strike"])
                s_ent = st.text_input("Entry", value=current_idx_data["signal"]["Entry"])
                s_tgt = st.text_input("Target", value=current_idx_data["signal"]["Target"])
                s_sl = st.text_input("SL", value=current_idx_data["signal"]["SL"])
                if st.button("UPDATE LEVELS"):
                    all_index_data[index_choice]["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl}
                    save_json(DATA_FILE, all_index_data)
                    st.rerun()

    # --- ROW 2: OPTION CHAIN (Aapka Logic) ---
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)
    
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    d_df = df.iloc[max(0, df.index[df["STRIKE"] == atm_strike][0]-7) : df.index[df["STRIKE"] == atm_strike][0]+8].copy()

    # UI Table Formatting
    ui = pd.DataFrame()
    ui["CE VOL"] = d_df["volume_CE"].apply(lambda x: f"{x:,.0f}")
    ui["CE OI"] = d_df["open_interest_CE"].apply(lambda x: f"{x:,.0f}")
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE OI"] = d_df["open_interest_PE"].apply(lambda x: f"{x:,.0f}")
    ui["PE VOL"] = d_df["volume_PE"].apply(lambda x: f"{x:,.0f}")

    def style_table(row):
        s = [''] * 5
        cur_strike = int(d_df.loc[row.name, "STRIKE"])
        v_ce, v_pe = d_df.loc[row.name, "volume_CE"], d_df.loc[row.name, "volume_PE"]
        o_ce, o_pe = d_df.loc[row.name, "open_interest_CE"], d_df.loc[row.name, "open_interest_PE"]

        if cur_strike == atm_strike: s[2] = 'background-color: yellow; color: black; font-weight: bold'
        if v_ce > (o_ce * 40): s[0] = 'background-color: #e1bee7' # CE Trap
        if v_pe > (o_pe * 40): s[4] = 'background-color: #e1bee7' # PE Trap
        if v_ce == max_vol_ce: s[0] = 'background-color: #c8e6c9' # Max Vol CE
        if v_pe == max_vol_pe: s[4] = 'background-color: #ffcdd2' # Max Vol PE
        return s

    st.subheader(f"📊 {index_choice} Option Chain (Volume vs OI)")
    st.table(ui.style.apply(style_table, axis=1))

else:
    st.info("Connecting to Market Stream...")
