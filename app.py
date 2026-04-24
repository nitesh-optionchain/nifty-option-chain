import streamlit as st
import pandas as pd
import json, os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & CSS SETUP =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# CSS to ensure high contrast and visibility
st.markdown("""
    <style>
    .stDataFrame { border: 1px solid #444; border-radius: 10px; }
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #00e676; }
    </style>
    """, unsafe_allow_html=True)

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.is_super_admin = False

# ================= 2. DATA LOAD/SAVE =================
DATA_FILE = "admin_signals_v5.json"
USER_FILE = "authorized_users.json"

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return json.load(f)
        except: pass
    return default

def save_json(file, data):
    with open(file, "w") as f: json.dump(data, f)

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

# ================= 4. SDK & DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.nubra)
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

try:
    res = market.option_chain(index_choice, exchange=target_exch)
    chain = res.chain
    raw_spot = getattr(chain, 'underlying_price', 0) or getattr(chain.ce[0], 'underlying_price', 0)
    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    
    # Process CE/PE and fix Strikes
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike_price"].apply(lambda x: int(x/100) if x > 100000 else int(x))
except:
    st.warning("Fetching Live Data...")
    st.stop()

# ================= 5. ADMIN & SIGNALS =================
all_sigs = load_json(DATA_FILE, {
    "NIFTY": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"},
    "SENSEX": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"}
})
sig = all_sigs[index_choice]

if st.session_state.is_super_admin:
    with st.expander("🛠️ ADMIN CONTROL PANEL"):
        c1, c2, c3, c4 = st.columns(4)
        v_stk = c1.text_input("Strike", sig['stk'])
        v_buy = c2.text_input("Buy Price", sig['buy'])
        v_tgt = c3.text_input("Target", sig['tgt'])
        v_sl = c4.text_input("SL", sig['sl'])
        if st.button("UPDATE DATA"):
            all_sigs[index_choice] = {"stk":v_stk, "buy":v_buy, "tgt":v_tgt, "sl":v_sl, "sup":sig['sup'], "res":sig['res']}
            save_json(DATA_FILE, all_sigs); st.rerun()

# Metrics
st.markdown(f"### 📊 {index_choice} Live Analysis")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🎯 STRIKE", sig['stk'])
m2.metric("💰 BUY", sig['buy'])
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

ui = pd.DataFrame()
# Layout: OI CHG, OI, VOL | STRIKE | VOL, OI, OI CHG
ui["OI CHG (CE)"] = d_df.apply(lambda r: f"{r['open_interest_CE'] - r.get('previous_close_oi_CE', r['open_interest_CE']):+,}", axis=1)
ui["OI (CE)"] = d_df["open_interest_CE"]
ui["VOL (CE)"] = d_df["volume_CE"]
ui["STRIKE"] = d_df["STRIKE"]
ui["VOL (PE)"] = d_df["volume_PE"]
ui["OI (PE)"] = d_df["open_interest_PE"]
ui["OI CHG (PE)"] = d_df.apply(lambda r: f"{r['open_interest_PE'] - r.get('previous_close_oi_PE', r['open_interest_PE']):+,}", axis=1)

# ================= 7. STYLING (COLORS & LAMBA LINE) =================
def apply_final_styles(row):
    colors = [''] * len(row)
    c_stk = int(row["STRIKE"])
    
    # 1. Strike Column (Grey)
    colors[3] = 'background-color: #333333; color: white; font-weight: bold'

    # 2. Heatmap (70% Max OI)
    if (float(row["OI (CE)"]) / max_oi_ce) >= 0.7: colors[1] = 'background-color: #E65100; color: white'
    if (float(row["OI (PE)"]) / max_oi_pe) >= 0.7: colors[5] = 'background-color: #E65100; color: white'

    # 3. ATM (Yellow)
    if c_stk == atm_strike: colors[3] = 'background-color: #FFD600; color: black'

    # 4. Break Even (Lamba Line)
    if c_stk == be_strike:
        line_bg = "#0D47A1" if df["open_interest_PE"].sum() > df["open_interest_CE"].sum() else "#880E4F"
        colors = [f'background-color: {line_bg}; color: white; border-top: 3px solid yellow; border-bottom: 3px solid yellow;'] * len(row)
        
    return colors

# Display Table
st.dataframe(
    ui.style.apply(apply_final_styles, axis=1),
    use_container_width=True,
    height=750
)

if st.sidebar.button("🔒 Logout"):
    st.session_state.is_auth = False
    st.rerun()
