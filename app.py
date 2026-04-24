import streamlit as st
import pandas as pd
import json, os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# ================= 1. SETTINGS & CSS =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e1e1e; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

# ================= 2. DATA LOAD/SAVE =================
DATA_FILE = "admin_signals_live.json"
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

try:
    res = market.option_chain(index_choice, exchange=target_exch)
    chain = res.chain
    
    # 100% Accurate Spot Calculation
    raw_spot = getattr(chain, 'underlying_price', 0)
    if raw_spot == 0: raw_spot = chain.ce[0].underlying_price
    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot

    # Data Extract
    ce_list = [vars(x) for x in chain.ce]
    pe_list = [vars(x) for x in chain.pe]
    df = pd.merge(pd.DataFrame(ce_list), pd.DataFrame(pe_list), on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    
    # STRIKE CORRECTION (Sabse important fix)
    df["STRIKE"] = df["strike_price"].apply(lambda x: int(x/100) if x > 100000 else int(x))
except Exception as e:
    st.error(f"Market Close or Data Loading... Error: {e}")
    st.stop()

# ================= 5. ADMIN DATA =================
all_sigs = load_json(DATA_FILE, {
    "NIFTY": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"},
    "SENSEX": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"}
})
sig = all_sigs[index_choice]

if st.session_state.is_super_admin:
    with st.expander("🛠️ UPDATE MANUAL LEVELS"):
        c1, c2, c3, c4 = st.columns(4)
        v_stk = c1.text_input("Strike", sig['stk'])
        v_buy = c2.text_input("Buy", sig['buy'])
        v_tgt = c3.text_input("Target", sig['tgt'])
        v_sl = c4.text_input("SL", sig['sl'])
        if st.button("SAVE"):
            all_sigs[index_choice] = {"stk":v_stk, "buy":v_buy, "tgt":v_tgt, "sl":v_sl, "sup":sig['sup'], "res":sig['res']}
            with open(DATA_FILE, "w") as f: json.dump(all_sigs, f)
            st.rerun()

# Metrics Display
st.markdown(f"### 🛡️ {index_choice} Live Tracker")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🎯 CALL/PUT", sig['stk'])
m2.metric("💰 BUY AT", sig['buy'])
m3.metric("📈 TARGET", sig['tgt'])
m4.metric("📉 SL", sig['sl'])

# ================= 6. OPTION CHAIN LOGIC =================
atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
be_strike = int(df.loc[(df["open_interest_CE"] + df["open_interest_PE"]).idxmax(), "STRIKE"])
max_oi_ce = df["open_interest_CE"].max() or 1
max_oi_pe = df["open_interest_PE"].max() or 1

# Filter ATM +/- 10
idx_atm = df.index[df["STRIKE"] == atm_strike][0]
d_df = df.iloc[max(idx_atm-10, 0): idx_atm+11].copy()

# Final UI Columns
ui = pd.DataFrame()
ui["OI CHG (CE)"] = d_df.apply(lambda r: f"{int(r['open_interest_CE'] - r.get('previous_close_oi_CE', r['open_interest_CE'])):+,}", axis=1)
ui["OI (CE)"] = d_df["open_interest_CE"].astype(int)
ui["VOL (CE)"] = d_df["volume_CE"].astype(int)
ui["STRIKE"] = d_df["STRIKE"]
ui["VOL (PE)"] = d_df["volume_PE"].astype(int)
ui["OI (PE)"] = d_df["open_interest_PE"].astype(int)
ui["OI CHG (PE)"] = d_df.apply(lambda r: f"{int(r['open_interest_PE'] - r.get('previous_close_oi_PE', r['open_interest_PE'])):+,}", axis=1)

# ================= 7. STYLING (THE FINAL TOUCH) =================
def final_style(row):
    styles = [''] * len(row)
    c_stk = int(row["STRIKE"])
    
    # Strike Column Grey
    styles[3] = 'background-color: #333333; color: white; font-weight: bold'

    # Heatmap 70%
    if (row["OI (CE)"] / max_oi_ce) >= 0.7: styles[1] = 'background-color: #E65100; color: white'
    if (row["OI (PE)"] / max_oi_pe) >= 0.7: styles[5] = 'background-color: #E65100; color: white'

    # ATM Yellow
    if c_stk == atm_strike: styles[3] = 'background-color: #FFD600; color: black'

    # Break Even Line
    if c_stk == be_strike:
        line_color = "#0D47A1" if df["open_interest_PE"].sum() > df["open_interest_CE"].sum() else "#880E4F"
        styles = [f'background-color: {line_color}; color: white; font-weight: bold; border-top: 2px solid yellow; border-bottom: 2px solid yellow;'] * len(row)
        
    return styles

st.dataframe(ui.style.apply(final_style, axis=1), use_container_width=True, height=800)
