import streamlit as st
import pandas as pd
import json, os, time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & SESSION SETUP =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"
    st.session_state.is_super_admin = False

# ================= 2. DATA PERSISTENCE =================
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

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin X"})
SUPER_ADMINS = ["9304768496", "7982046438"]

# ================= 3. LOGIN FIREWALL =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            u_id = st.text_input("Mobile ID", type="password")
            if st.form_submit_button("LOGIN"):
                if u_id in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[u_id]
                    st.session_state.is_super_admin = u_id in SUPER_ADMINS
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SDK & HEADER DATA =================
st_autorefresh(interval=5000, key="datarefresh")

if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market = MarketData(st.session_state.nubra)

def get_spot_info(idx, exch):
    try:
        res = market.option_chain(idx, exchange=exch)
        raw = getattr(res.chain, 'underlying_price', getattr(res.chain.ce[0], 'underlying_price', 0))
        spot = raw / 100 if raw > 100000 else raw
        return spot, res
    except: return 0.0, None

# Fetch Live Prices for Header
n_spot, n_res = get_spot_info("NIFTY", "NSE")
s_spot, s_res = get_spot_info("SENSEX", "BSE")

h1, h2 = st.columns(2)
h1.markdown(f"<div style='background-color:#1e1e1e; padding:10px; border-radius:10px; border-left:5px solid #00e676; text-align:center;'><p style='color:white; margin:0;'>NIFTY 50</p><h2 style='color:#00e676; margin:0;'>{n_spot:,.2f}</h2></div>", unsafe_allow_html=True)
h2.markdown(f"<div style='background-color:#1e1e1e; padding:10px; border-radius:10px; border-left:5px solid #ff5252; text-align:center;'><p style='color:white; margin:0;'>SENSEX</p><h2 style='color:#ff5252; margin:0;'>{s_spot:,.2f}</h2></div>", unsafe_allow_html=True)

# ================= 5. ADMIN CONTROLS & SIGNALS =================
index_choice = st.sidebar.selectbox("Select Dashboard Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"
cur_spot = n_spot if index_choice == "NIFTY" else s_spot
cur_res = n_res if index_choice == "NIFTY" else s_res

all_sigs = load_json(DATA_FILE, {
    "NIFTY": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"},
    "SENSEX": {"stk": "-", "buy": "-", "tgt": "-", "sl": "-", "sup": "-", "res": "-"}
})
sig = all_sigs[index_choice]

if st.session_state.is_super_admin:
    with st.expander(f"🛠️ ADMIN PANEL ({index_choice})"):
        t1, t2 = st.tabs(["Signal Update", "Users"])
        with t1:
            c1, c2, c3, c4 = st.columns(4)
            v_stk = c1.text_input("Strike", sig['stk'])
            v_buy = c2.text_input("Buy Price", sig['buy'])
            v_tgt = c3.text_input("Target", sig['tgt'])
            v_sl = c4.text_input("SL", sig['sl'])
            v_sup = st.text_input("Support Strike", sig['sup'])
            v_res = st.text_input("Resistance Strike", sig['res'])
            if st.button("UPDATE DASHBOARD"):
                all_sigs[index_choice] = {"stk":v_stk, "buy":v_buy, "tgt":v_tgt, "sl":v_sl, "sup":v_sup, "res":v_res}
                save_json(DATA_FILE, all_sigs); st.rerun()
        with t2:
            new_id = st.text_input("New User ID")
            new_name = st.text_input("User Name")
            if st.button("ADD USER"):
                ADMIN_DB[new_id] = new_name
                save_json(USER_FILE, ADMIN_DB); st.success("Added")

# Metric Display
st.markdown("### 📊 Live Manual Signals")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🎯 STRIKE", sig['stk'])
m2.metric("💰 BUY", sig['buy'])
m3.metric("📈 TARGET", sig['tgt'])
m4.metric("📉 SL", sig['sl'])
m5.metric("🔴 SUP", sig['sup'])
m6.metric("🟢 RES", sig['res'])

# ================= 6. OPTION CHAIN & GREEKS =================
if not cur_res or not cur_res.chain:
    st.info("Loading market data...")
    st.stop()

def process_chain(side_data):
    rows = []
    for x in side_data:
        d = vars(x)
        d['delta'] = getattr(x.greeks, 'delta', 0) if hasattr(x, 'greeks') else 0
        d['gamma'] = getattr(x.greeks, 'gamma', 0) if hasattr(x, 'greeks') else 0
        rows.append(d)
    return pd.DataFrame(rows)

df_ce = process_chain(cur_res.chain.ce)
df_pe = process_chain(cur_res.chain.pe)
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Stable OI Snap
state_key = f"stable_snap_{index_choice}"
if state_key not in st.session_state:
    st.session_state[state_key] = df.copy()

def get_stable_ui(row, side):
    curr = row[f"open_interest_{side}"]
    snap = st.session_state[state_key].set_index("STRIKE")
    prev = snap.loc[row["STRIKE"], f"open_interest_{side}"] if row["STRIKE"] in snap.index else curr
    diff = curr - prev
    max_oi = df[f"open_interest_{side}"].max() or 1
    pct = (curr / max_oi * 100)
    return f"{curr:,.0f}\n({diff:+,})\n{pct:.1f}%"

# Logic for BE and Trap
be_strike = int(df.loc[(df["open_interest_CE"] + df["open_interest_PE"]).idxmax(), "STRIKE"])
bullish = df["open_interest_PE"].sum() > df["open_interest_CE"].sum()
atm_strike = df.loc[(df["STRIKE"] - cur_spot).abs().idxmin(), "STRIKE"]

# Filter View (ATM +- 7 strikes)
idx_atm = df.index[df["STRIKE"] == atm_strike][0]
d_df = df.iloc[max(idx_atm-7,0): idx_atm+8].copy()

# Table UI Build
ui = pd.DataFrame()
ui["OI CHG (CE)"] = d_df.apply(lambda r: get_stable_ui(r, "CE"), axis=1)
ui["OI (CE)"] = d_df["open_interest_CE"]
ui["VOL (CE)"] = d_df["volume_CE"]
ui["STRIKE"] = d_df["STRIKE"]
ui["VOL (PE)"] = d_df["volume_PE"]
ui["OI (PE)"] = d_df["open_interest_PE"]
ui["OI CHG (PE)"] = d_df.apply(lambda r: get_stable_ui(r, "PE"), axis=1)

# ================= 7. LAMBA LINE STYLING =================
def apply_styles(row):
    s = [''] * len(row)
    c_stk = int(row["STRIKE"])
    
    # Default Strike Grey
    s[3] = 'background-color: #424242; color: white; font-weight: bold'

    try:
        ce_pct = float(row.iloc[0].split('\n')[-1].replace('%',''))
        pe_pct = float(row.iloc[6].split('\n')[-1].replace('%',''))
        
        # Heatmap Colors (>70%)
        if ce_pct >= 70: s[0] = 'background-color: #E65100; color: white' # Deep Orange
        if pe_pct >= 70: s[6] = 'background-color: #E65100; color: white'

        # THE "LAMBA LINE" (Break Even Point)
        if c_stk == be_strike:
            line_color = "#0D47A1" if bullish else "#880E4F" # Deep Blue vs Maroon
            # Check for False Trap using Delta (integrated check)
            ce_delta = df.loc[df["STRIKE"]==c_stk, "delta_CE"].values[0]
            pe_delta = abs(df.loc[df["STRIKE"]==c_stk, "delta_PE"].values[0])
            
            if (bullish and ce_delta < 0.45) or (not bullish and pe_delta < 0.45):
                # Trap color (Brown)
                s = ['background-color: #3e2723; color: #ffab00; font-weight: bold; border-top: 3px solid #ffab00; border-bottom: 3px solid #ffab00;'] * len(row)
            else:
                # Solid Lamba Line
                s = [f'background-color: {line_color}; color: white; font-weight: bold; border-top: 4px solid yellow; border-bottom: 4px solid yellow;'] * len(row)

        # ATM Highlight
        elif c_stk == atm_strike:
            s[3] = 'background-color: #FFD600; color: black; font-weight: bold'

        # Manual S/R Highlight
        if str(c_stk) == sig['sup']: s[3] = 'background-color: #d32f2f; color: white'
        if str(c_stk) == sig['res']: s[3] = 'background-color: #388e3c; color: white'

    except: pass
    return s

st.subheader(f"📊 {index_choice} Option Chain Analysis")
st.table(ui.style.apply(apply_styles, axis=1))

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()
