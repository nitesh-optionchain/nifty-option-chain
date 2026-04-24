import streamlit as st
import pandas as pd
import json, os
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False

if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
market = MarketData(st.session_state.nubra)

# ================= 2. SIMPLE WORKING HEADER =================
def get_live_price(idx, exch):
    try:
        res = market.option_chain(idx, exchange=exch)
        lp = getattr(res.chain, 'underlying_price', 0)
        if lp == 0 and len(res.chain.ce) > 0: lp = res.chain.ce[0].underlying_price
        return lp / 100 if lp > 100000 else lp, res
    except: return 0.0, None

n_p, n_res = get_live_price("NIFTY", "NSE")
s_p, s_res = get_live_price("SENSEX", "BSE")

h1, h2 = st.columns(2)
h1.markdown(f"<div style='background-color:#1e1e1e; padding:10px; border-radius:10px; border-left:5px solid #00e676; text-align:center;'><p style='color:white; margin:0;'>NIFTY 50</p><h2 style='color:#00e676; margin:0;'>{n_p:,.2f}</h2></div>", unsafe_allow_html=True)
h2.markdown(f"<div style='background-color:#1e1e1e; padding:10px; border-radius:10px; border-left:5px solid #ff5252; text-align:center;'><p style='color:white; margin:0;'>SENSEX</p><h2 style='color:#ff5252; margin:0;'>{s_p:,.2f}</h2></div>", unsafe_allow_html=True)

# ================= 3. AUTH & SIGNALS =================
SIG_FILE = "admin_signals_final.json"
if not st.session_state.is_auth:
    with st.form("Login"):
        u_id = st.text_input("Mobile ID", type="password")
        if st.form_submit_button("LOGIN"):
            if u_id in ["9304768496", "7982046438"]:
                st.session_state.is_auth, st.session_state.u_id = True, u_id
                st.rerun()
    st.stop()

def load_sigs():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f: return json.load(f)
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}, 
            "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

all_sigs = load_sigs()
idx_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
sig = all_sigs[idx_choice]

if st.session_state.u_id in ["9304768496", "7982046438"]:
    with st.expander("🛠️ MANUAL ENTRY"):
        c = st.columns(4)
        v_stk = c[0].text_input("Signal", sig['stk'])
        v_buy = c[1].text_input("Buy", sig['buy'])
        v_tgt = c[2].text_input("Target", sig['tgt'])
        v_sl = c[3].text_input("SL", sig['sl'])
        v_sup = st.text_input("Support", sig['sup'])
        v_res = st.text_input("Resistance", sig['res'])
        if st.button("UPDATE"):
            all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
            with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
            st.rerun()

st.markdown("### 📊 Levels")
m = st.columns(6)
m[0].metric("🎯 SIGNAL", sig['stk']); m[1].metric("💰 ENTRY", sig['buy']); m[2].metric("📈 TGT", sig['tgt'])
m[3].metric("📉 SL", sig['sl']); m[4].metric("🔴 SUP", sig['sup']); m[5].metric("🟢 RES", sig['res'])

# ================= 4. DATA & STYLE =================
cur_res = n_res if idx_choice == "NIFTY" else s_res
cur_spot = n_p if idx_choice == "NIFTY" else s_p

if cur_res:
    chain = cur_res.chain
    def parse(data):
        return pd.DataFrame([{"strike": x.strike_price, "oi": getattr(x, 'open_interest', 0), 
                             "prev_oi": getattr(x, 'previous_close_oi', 0), "vol": getattr(x, 'volume', 0)} for x in data])

    df = pd.merge(parse(chain.ce), parse(chain.pe), on="strike", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
    atm = df.loc[(df["STRIKE"] - cur_spot).abs().idxmin(), "STRIKE"]
    be = int(df.loc[(df["oi_CE"] + df["oi_PE"]).idxmax(), "STRIKE"])
    mx_oi_ce, mx_oi_pe = df["oi_CE"].max() or 1, df["oi_PE"].max() or 1
    mx_vol_ce, mx_vol_pe = df["vol_CE"].max() or 1, df["vol_PE"].max() or 1

    idx_atm = df.index[df["STRIKE"] == atm][0]
    d_df = df.iloc[max(idx_atm-10, 0): idx_atm+11].copy()

    ui = pd.DataFrame()
    def get_oi_chg(row, s):
        diff = row[f"oi_{s}"] - row[f"prev_oi_{s}"]
        pct = (diff / row[f"prev_oi_{s}"] * 100) if row[f"prev_oi_{s}"] > 0 else 0
        return f"{diff:+,}\n({pct:+.1f}%)"

    ui["OI CHG % CE"] = d_df.apply(lambda r: get_oi_chg(r, "CE"), axis=1)
    ui["OI (CE)"] = d_df["oi_CE"].astype(int)
    ui["VOL (CE)"] = d_df["vol_CE"].astype(int)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["VOL (PE)"] = d_df["vol_PE"].astype(int)
    ui["OI (PE)"] = d_df["oi_PE"].astype(int)
    ui["OI CHG % PE"] = d_df.apply(lambda r: get_oi_chg(r, "PE"), axis=1)

    def apply_style(row):
        s = [''] * len(row)
        stk = int(row["STRIKE"])
        s[3] = 'background-color: #333333; color: white;' 
        
        # 70% Colour Code
        if (row["OI (CE)"] / mx_oi_ce) >= 0.7: s[1] = 'background-color: #E65100; color: white;'
        if (row["VOL (CE)"] / mx_vol_ce) >= 0.7: s[2] = 'background-color: #4A148C; color: white;'
        if (row["OI (PE)"] / mx_oi_pe) >= 0.7: s[5] = 'background-color: #E65100; color: white;'
        if (row["VOL (PE)"] / mx_vol_pe) >= 0.7: s[4] = 'background-color: #4A148C; color: white;'

        if stk == atm: s[3] = 'background-color: #FFD600; color: black;'
        if str(stk) == sig['sup']: s[3] = 'background-color: #d32f2f; color: white;'
        if str(stk) == sig['res']: s[3] = 'background-color: #388e3c; color: white;'

        if stk == be:
            bg = "#0D47A1" if df["oi_PE"].sum() > df["oi_CE"].sum() else "#880E4F"
            s = [f'background-color: {bg}; color: white; font-weight: bold; border-top: 2px solid yellow; border-bottom: 2px solid yellow;'] * len(row)
        return s

    st.table(ui.style.apply(apply_style, axis=1))
