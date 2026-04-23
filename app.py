from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import json, os

# ================= 1. CONFIG & AUTH STATE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"

# ================= 2. FILE STORAGE =================
DATA_FILE = "admin_data_v2.json" 
USER_FILE = "authorized_users.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})

# ================= 3. LOGIN FIREWALL =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="refresh")
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. SDK & DATA FETCH (FIXED FOR NIFTY) =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain, 'underlying_price', 0)
        if raw_spot == 0 and chain.ce:
            raw_spot = getattr(chain.ce[0], 'underlying_price', 0)
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    
    # NIFTY Strike Error Correction Logic
    df["STRIKE_VAL"] = df["strike_price"].apply(lambda x: int(x/100) if (index_choice == "NIFTY" and x > 100000) or (index_choice == "SENSEX" and x > 500000) else int(x))

    max_oi_ce = df["open_interest_CE"].max() or 1
    max_oi_pe = df["open_interest_PE"].max() or 1
    
    be_res_strike = int(df.loc[df["open_interest_CE"].idxmax(), "STRIKE_VAL"])
    be_sup_strike = int(df.loc[df["open_interest_PE"].idxmax(), "STRIKE_VAL"])

    # ================= 6. TABLE UI LOGIC =================
    def fmt_val(val, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n{pct:.1f}%"

    # Signal Logic inside STRIKE column ONLY for Break-even lines
    def get_strike_signal(row):
        stk = int(row["STRIKE_VAL"])
        if stk == be_res_strike and spot >= be_res_strike:
            return "⬆️ BUY CE"
        if stk == be_sup_strike and spot <= be_sup_strike:
            return "⬇️ BUY PE"
        return str(stk)

    atm_strike = df.loc[(df["STRIKE_VAL"] - spot).abs().idxmin(), "STRIKE_VAL"]
    atm_idx = df.index[df["STRIKE_VAL"] == atm_strike][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI (%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], max_oi_ce), axis=1)
    ui["CE VOL"] = d_df["volume_CE"].apply(lambda x: f"{x:,.0f}")
    ui["STRIKE"] = d_df.apply(get_strike_signal, axis=1) 
    ui["PE VOL"] = d_df["volume_PE"].apply(lambda x: f"{x:,.0f}")
    ui["PE OI (%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], max_oi_pe), axis=1)
    ui["STK_RAW"] = d_df["STRIKE_VAL"] 

    def style_table(row):
        s = [''] * len(row)
        cur_strike = int(row["STK_RAW"])
        s[2] = 'background-color:#f0f2f6;color:black;font-weight:bold' 
        
        if cur_strike == be_res_strike: 
            s = ['border: 2px solid blue; font-weight: bold'] * len(row)
            if spot >= be_res_strike: s = ['background-color: #008000; color: white; font-weight: bold'] * len(row)
        
        if cur_strike == be_sup_strike: 
            s = ['border: 2px solid red; font-weight: bold'] * len(row)
            if spot <= be_sup_strike: s = ['background-color: #FF0000; color: white; font-weight: bold'] * len(row)

        if cur_strike == int(atm_strike): 
            if 'background-color' not in s[2]: s[2] = 'background-color:yellow;color:black'
        return s

    st.subheader(f"📊 {index_choice} Option Chain")
    st.table(ui.iloc[:, :5].style.apply(style_table, axis=1))
else:
    st.info(f"{index_choice} ka data load ho raha hai...")
