import streamlit as st
import pandas as pd
import json, os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# 1. Config
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# 2. Connection Fix (Yahan apni Key aur Secret dalo bhai)
if "nubra" not in st.session_state:
    try:
        # APNI KEY YAHAN DALO AGAR .ENV KAAM NAHI KAR RAHA
        # st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, api_key="AP123...", secret="SE123...")
        st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except Exception as e:
        st.error(f"API Error: {e}")
        st.stop()

market = MarketData(st.session_state.nubra)

# 3. Fast Data Fetch
def get_data(idx, exch):
    try:
        res = market.option_chain(idx, exchange=exch)
        p = getattr(res.chain, 'underlying_price', 0)
        if p == 0 and len(res.chain.ce) > 0: p = res.chain.ce[0].underlying_price
        return (p/100 if p > 100000 else p), res
    except: return 0.0, None

n_p, n_res = get_data("NIFTY", "NSE")
s_p, s_res = get_data("SENSEX", "BSE")

# 4. Header
c1, c2 = st.columns(2)
c1.metric("NIFTY 50", f"{n_p:,.2f}")
c2.metric("SENSEX", f"{s_p:,.2f}")

# 5. Admin & Manual Signals
SIG_FILE = "trading_data.json"
if "is_auth" not in st.session_state: st.session_state.is_auth = False

if not st.session_state.is_auth:
    with st.form("Login"):
        u_id = st.text_input("Mobile ID", type="password")
        if st.form_submit_button("LOGIN"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth = True
                st.rerun()
    st.stop()

def load_json():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}, "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

all_sigs = load_json()
idx_choice = st.sidebar.selectbox("Index", ["NIFTY", "SENSEX"])
sig = all_sigs[idx_choice]

with st.expander("🛠️ EDIT LEVELS"):
    cols = st.columns(4)
    v_stk = cols[0].text_input("Signal", sig['stk'])
    v_buy = cols[1].text_input("Buy", sig['buy'])
    v_tgt = cols[2].text_input("Tgt", sig['tgt'])
    v_sl = cols[3].text_input("SL", sig['sl'])
    v_sup = st.text_input("Support", sig['sup'])
    v_res = st.text_input("Resistance", sig['res'])
    if st.button("SAVE"):
        all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
        with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
        st.rerun()

# 6. Table Display
cur_res = n_res if idx_choice == "NIFTY" else s_res
cur_spot = n_p if idx_choice == "NIFTY" else s_p

if cur_res:
    chain = cur_res.chain
    def parse(d):
        return pd.DataFrame([{"strike": x.strike_price, "oi": getattr(x, 'open_interest', 0), "vol": getattr(x, 'volume', 0)} for x in d])
    
    df = pd.merge(parse(chain.ce), parse(chain.pe), on="strike", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
    mx_oi_ce, mx_vol_ce = df["oi_CE"].max() or 1, df["vol_CE"].max() or 1
    mx_oi_pe, mx_vol_pe = df["oi_PE"].max() or 1, df["vol_PE"].max() or 1
    atm = df.loc[(df["STRIKE"] - cur_spot).abs().idxmin(), "STRIKE"]
    
    idx_atm = df.index[df["STRIKE"] == atm][0]
    d_df = df.iloc[max(idx_atm-10, 0): idx_atm+11].copy()

    def style_row(row):
        s = [''] * len(row)
        stk = int(row["STRIKE"])
        # 70% Colour Logic
        if (row["oi_CE"] / mx_oi_ce) >= 0.7: s[1] = 'background-color: #E65100; color: white;'
        if (row["vol_CE"] / mx_vol_ce) >= 0.7: s[2] = 'background-color: #4A148C; color: white;'
        if stk == atm: s[3] = 'background-color: #FFD600; color: black;'
        if str(stk) == sig['sup']: s[3] = 'background-color: #d32f2f; color: white;'
        if str(stk) == sig['res']: s[3] = 'background-color: #388e3c; color: white;'
        return s

    # Re-arranging for display
    ui = d_df[["oi_CE", "vol_CE", "STRIKE", "vol_PE", "oi_PE"]]
    st.table(ui.style.apply(style_row, axis=1))
else:
    st.error("API se data nahi aa raha. Please check Credentials.")
