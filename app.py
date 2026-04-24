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

# ================= 2. ROBUST HEADER LOGIC =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.nubra)

def get_market_status(idx_name, exch):
    try:
        res = market.option_chain(idx_name, exchange=exch)
        chain = res.chain
        
        # 1. Sabse pehle underlying_price check karo
        raw_curr = getattr(chain, 'underlying_price', 0)
        
        # 2. Agar 0 hai, toh CE side ki pehli strike ka underlying_price uthao
        if raw_curr == 0 and hasattr(chain, 'ce') and len(chain.ce) > 0:
            raw_curr = getattr(chain.ce[0], 'underlying_price', 0)
            
        curr = raw_curr / 100 if raw_curr > 100000 else raw_curr
        
        # Previous Close Logic for % Change
        raw_prev = getattr(chain, 'previous_close', curr)
        if raw_prev > 100000: raw_prev = raw_prev / 100
        
        change = round(curr - raw_prev, 2)
        p_chg = round((change / raw_prev * 100), 2) if raw_prev > 0 else 0.00
        
        return round(curr, 2), change, p_chg, res
    except Exception as e:
        return 0.00, 0.00, 0.00, None

# Data Fetching
n_p, n_c, n_pc, n_res = get_market_status("NIFTY", "NSE")
s_p, s_c, s_pc, s_res = get_market_status("SENSEX", "BSE")

# Header Cards UI
def draw_card(title, price, chg, pct):
    color = "#00e676" if chg >= 0 else "#ff5252"
    arrow = "▲" if chg >= 0 else "▼"
    # Agar price 0 hai toh 'Loading' dikhaye
    display_price = f"{price:,.2f}" if price > 0 else "FETCHING..."
    return f"""
    <div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border-bottom:5px solid {color}; text-align:center;'>
        <p style='color:#aaa; margin:0; font-size:14px;'>{title}</p>
        <h2 style='color:white; margin:5px 0;'>{display_price}</h2>
        <p style='color:{color}; margin:0; font-size:18px; font-weight:bold;'>
            {arrow} {chg:+,.2f} ({pct:+,.2f}%)
        </p>
    </div>
    """

c1, c2 = st.columns(2)
c1.markdown(draw_card("NIFTY 50", n_p, n_c, n_pc), unsafe_allow_html=True)
c2.markdown(draw_card("SENSEX", s_p, s_c, s_pc), unsafe_allow_html=True)

# ================= 3. AUTH & MANUAL DATA =================
SIG_FILE = "admin_signals_v10.json"
if not st.session_state.is_auth:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        with st.form("Login"):
            u_id = st.text_input("Mobile ID", type="password")
            if st.form_submit_button("LOGIN"):
                if u_id in ["9304768496", "7982046438"]:
                    st.session_state.is_auth, st.session_state.u_id = True, u_id
                    st.rerun()
    st.stop()

def load_data():
    if os.path.exists(SIG_FILE):
        try:
            with open(SIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {"NIFTY": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"},
            "SENSEX": {"stk":"-","buy":"-","tgt":"-","sl":"-","sup":"-","res":"-"}}

all_sigs = load_data()
idx_choice = st.sidebar.selectbox("Dashboard", ["NIFTY", "SENSEX"])
sig = all_sigs[idx_choice]

# Admin Panel
if st.session_state.u_id in ["9304768496", "7982046438"]:
    with st.expander("🛠️ MANUAL ENTRY PANEL"):
        cols = st.columns(4)
        v_stk = cols[0].text_input("Signal", sig['stk'])
        v_buy = cols[1].text_input("Buy", sig['buy'])
        v_tgt = cols[2].text_input("Target", sig['tgt'])
        v_sl = cols[3].text_input("SL", sig['sl'])
        v_sup = st.text_input("Support Strike", sig['sup'])
        v_res = st.text_input("Resistance Strike", sig['res'])
        if st.button("UPDATE"):
            all_sigs[idx_choice] = {"stk":v_stk,"buy":v_buy,"tgt":v_tgt,"sl":v_sl,"sup":v_sup,"res":v_res}
            with open(SIG_FILE, "w") as f: json.dump(all_sigs, f)
            st.rerun()

# Levels Metric
st.markdown("### 📊 Live Levels")
m = st.columns(6)
m[0].metric("🎯 SIGNAL", sig['stk']); m[1].metric("💰 ENTRY", sig['buy']); m[2].metric("📈 TARGET", sig['tgt'])
m[3].metric("📉 SL", sig['sl']); m[4].metric("🔴 SUP", sig['sup']); m[5].metric("🟢 RES", sig['res'])

# ================= 4. TABLE LOGIC (70% HEATMAP) =================
cur_res = n_res if idx_choice == "NIFTY" else s_res
cur_spot = n_p if idx_choice == "NIFTY" else s_p

if cur_res:
    chain = cur_res.chain
    def parse(data):
        return pd.DataFrame([{"strike": x.strike_price, "oi": getattr(x, 'open_interest', 0), 
                             "prev_oi": getattr(x, 'previous_close_oi', 0), "vol": getattr(x, 'volume', 0)} for x in data])

    df = pd.merge(parse(chain.ce), parse(chain.pe), on="strike", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = df["strike"].apply(lambda x: int(x/100) if x > 100000 else int(x))
    
    mx_oi_ce, mx_vol_ce = df["oi_CE"].max() or 1, df["vol_CE"].max() or 1
    mx_oi_pe, mx_vol_pe = df["oi_PE"].max() or 1, df["vol_PE"].max() or 1

    atm = df.loc[(df["STRIKE"] - cur_spot).abs().idxmin(), "STRIKE"]
    be = int(df.loc[(df["oi_CE"] + df["oi_PE"]).idxmax(), "STRIKE"])
    
    idx_atm = df.index[df["STRIKE"] == atm][0]
    d_df = df.iloc[max(idx_atm-10, 0): idx_atm+11].copy()

    # UI Table
    ui = pd.DataFrame()
    def get_oi_chg(row, s):
        diff = row[f"oi_{s}"] - row[f"prev_oi_{s}"]
        pct = (diff / row[f"prev_oi_{s}"] * 100) if row[f"prev_oi_{s}"] > 0 else 0
        return f"{diff:+,}\n({pct:+.1f}%)"

    ui["OI CHG (%) CE"] = d_df.apply(lambda r: get_oi_chg(r, "CE"), axis=1)
    ui["OI (CE)"] = d_df["oi_CE"].astype(int)
    ui["VOL (CE)"] = d_df["vol_CE"].astype(int)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["VOL (PE)"] = d_df["vol_PE"].astype(int)
    ui["OI (PE)"] = d_df["oi_PE"].astype(int)
    ui["OI CHG (%) PE"] = d_df.apply(lambda r: get_oi_chg(r, "PE"), axis=1)

    def final_style(row):
        s = [''] * len(row)
        stk = int(row["STRIKE"])
        s[3] = 'background-color: #333333; color: white;' 
        
        # Heatmap 70% Detection
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

    st.table(ui.style.apply(final_style, axis=1))
else:
    st.info("🔄 Connection established. Waiting for API to stream Nifty/Sensex data...")
