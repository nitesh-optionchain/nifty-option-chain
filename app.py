import streamlit as st
import pandas as pd
import json, os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# ================= 1. SETTINGS =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

# ================= 2. DATA LOAD/SAVE =================
DATA_FILE = "admin_signals.json"
USER_FILE = "authorized_users.json"

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return json.load(f)
        except: pass
    return default

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief"})

# ================= 3. LOGIN =================
if not st.session_state.is_auth:
    st.markdown("<h2 style='text-align: center;'>🛡️ SMART WEALTH LOGIN</h2>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        with st.form("Login"):
            u_id = st.text_input("Mobile ID", type="password")
            if st.form_submit_button("ENTER"):
                if u_id in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.is_super_admin = u_id in ["9304768496", "7982046438"]
                    st.rerun()
    st.stop()

# ================= 4. LIVE DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.nubra)
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

# Global Spot Init
spot = 0.0
df = pd.DataFrame()

try:
    res = market.option_chain(index_choice, exchange=target_exch)
    chain = res.chain
    
    # Accurate Spot Price
    raw_spot = getattr(chain, 'underlying_price', 0)
    if raw_spot == 0 and len(chain.ce) > 0:
        raw_spot = chain.ce[0].underlying_price
    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot

    # Simple Data Extract
    ce_rows = []
    for x in chain.ce:
        ce_rows.append({
            "strike_price": x.strike_price,
            "oi_CE": getattr(x, 'open_interest', 0),
            "vol_CE": getattr(x, 'volume', 0),
            "delta_CE": getattr(x.greeks, 'delta', 0) if hasattr(x, 'greeks') else 0
        })
    
    pe_rows = []
    for x in chain.pe:
        pe_rows.append({
            "strike_price": x.strike_price,
            "oi_PE": getattr(x, 'open_interest', 0),
            "vol_PE": getattr(x, 'volume', 0),
            "delta_PE": getattr(x.greeks, 'delta', 0) if hasattr(x, 'greeks') else 0
        })

    df_ce = pd.DataFrame(ce_rows)
    df_pe = pd.DataFrame(pe_rows)
    df = pd.merge(df_ce, df_pe, on="strike_price").fillna(0)
    
    # Strike Fix
    df["STRIKE"] = df["strike_price"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
except Exception as e:
    st.error(f"Waiting for Nubra API Data... (Refresh again in a moment)")
    st.stop()

# ================= 5. ADMIN DATA =================
all_sigs = load_json(DATA_FILE, {
    "NIFTY": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"},
    "SENSEX": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"}
})
sig = all_sigs[index_choice]

if st.session_state.is_super_admin:
    with st.expander("🛠️ UPDATE LEVELS"):
        c1, c2, c3, c4 = st.columns(4)
        v_stk = c1.text_input("Strike", sig['stk'])
        v_buy = c2.text_input("Buy", sig['buy'])
        v_tgt = c3.text_input("Target", sig['tgt'])
        v_sl = c4.text_input("SL", sig['sl'])
        if st.button("SAVE"):
            all_sigs[index_choice] = {"stk":v_stk, "buy":v_buy, "tgt":v_tgt, "sl":v_sl, "sup":sig['sup'], "res":sig['res']}
            with open(DATA_FILE, "w") as f: json.dump(all_sigs, f)
            st.rerun()

# Metrics
st.header(f"🛡️ {index_choice} Spot: {spot:,.2f}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🎯 SIGNAL", sig['stk'])
m2.metric("💰 ENTRY", sig['buy'])
m3.metric("📈 TARGET", sig['tgt'])
m4.metric("📉 SL", sig['sl'])

# ================= 6. TABLE LOGIC =================
if not df.empty:
    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    be_strike = int(df.loc[(df["oi_CE"] + df["oi_PE"]).idxmax(), "STRIKE"])
    max_oi_ce = df["oi_CE"].max() or 1
    max_oi_pe = df["oi_PE"].max() or 1

    # Filter Window
    idx_atm = df.index[df["STRIKE"] == atm_strike][0]
    d_df = df.iloc[max(idx_atm-10, 0): idx_atm+11].copy()

    # UI Columns
    ui = pd.DataFrame()
    ui["OI (CE)"] = d_df["oi_CE"].astype(int)
    ui["VOL (CE)"] = d_df["vol_CE"].astype(int)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["VOL (PE)"] = d_df["vol_PE"].astype(int)
    ui["OI (PE)"] = d_df["oi_PE"].astype(int)

    def style_row(row):
        styles = [''] * len(row)
        c_stk = int(row["STRIKE"])
        styles[2] = 'background-color: #333333; color: white;' # Strike Column

        if (row["OI (CE)"] / max_oi_ce) >= 0.7: styles[0] = 'background-color: #E65100; color: white'
        if (row["OI (PE)"] / max_oi_pe) >= 0.7: styles[4] = 'background-color: #E65100; color: white'
        
        if c_stk == be_strike:
            color = "#0D47A1" if df["oi_PE"].sum() > df["oi_CE"].sum() else "#880E4F"
            styles = [f'background-color: {color}; color: white; border: 2px solid yellow;'] * len(row)
        
        if c_stk == atm_strike:
            styles[2] = 'background-color: #FFD600; color: black'
        return styles

    st.table(ui.style.apply(style_row, axis=1))
else:
    st.info("Market data is not available right now. Please check API credentials or Market Hours.")
