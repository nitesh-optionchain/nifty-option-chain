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
    st.session_state.is_super_admin = False

# ================= 2. FILE STORAGE =================
DATA_FILE = "admin_data_v2.json" 
USER_FILE = "authorized_users.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: json.dump(data_to_save, f)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

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
                    st.session_state.is_super_admin = True if user_key in SUPER_ADMIN_IDS else False
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. LIVE HEADER =================
if index_choice == "SENSEX":
    tv_html = """<div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>{"symbol": "BSE:SENSEX", "width": "100%", "colorTheme": "light", "isTransparent": false, "locale": "en"}</script></div>"""
    components.html(tv_html, height=130)

# ================= 6. SDK & DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', getattr(chain, 'underlying_price', 0))
        spot = float(raw_spot) / 100 if raw_spot > 100000 else float(raw_spot)
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    
    # Strike Normalization for both Nifty and Sensex
    df["STRIKE"] = df["strike_price"].apply(lambda x: int(round(float(x)/100)) if x > 100000 else int(round(float(x))))

    # OI Change Logic
    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()

    def calc_stable_oi(row, side):
        curr_oi = float(row[f"open_interest_{side}"])
        init_df = st.session_state[state_key].set_index("STRIKE")
        strike = row["STRIKE"]
        prev_oi = float(init_df.loc[strike, f"open_interest_{side}"]) if strike in init_df.index else curr_oi
        return curr_oi - prev_oi

    df["oi_chg_CE"] = df.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
    df["oi_chg_PE"] = df.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

    # Calculation for Scaling and Lines
    max_oi_ce = df["open_interest_CE"].max() or 1
    max_oi_pe = df["open_interest_PE"].max() or 1
    max_vol_ce = df["volume_CE"].max() or 1
    max_vol_pe = df["volume_PE"].max() or 1
    max_chg_ce = df["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df["oi_chg_PE"].abs().max() or 1

    # RESISTANCE & SUPPORT STRIKES
    be_res_strike = int(df.loc[df["open_interest_CE"].idxmax(), "STRIKE"])
    be_sup_strike = int(df.loc[df["open_interest_PE"].idxmax(), "STRIKE"])

    # Auto Signal
    if spot >= be_res_strike:
        st.success(f"🚀 BREAKOUT: {index_choice} ABOVE {be_res_strike}")
    elif spot <= be_sup_strike:
        st.error(f"🩸 BREAKDOWN: {index_choice} BELOW {be_sup_strike}")

    # ================= 7. METRICS =================
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🎯 STRIKE", current_idx_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_idx_data["signal"]["Entry"])
    m3.metric("📈 TARGET", current_idx_data["signal"]["Target"])
    m4.metric("📉 SL", current_idx_data["signal"]["SL"])
    m5.metric("🟢 SUP", current_idx_data["sr"]["support"])
    m6.metric("🔴 RES", current_idx_data["sr"]["resistance"])

    # ================= 8. TABLE UI =================
    def fmt_val(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100):.1f}%"
    def fmt_chg(d, m): return f"{d:+,}\n{(d/m*100):.1f}%"

    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    atm_idx = df.index[df["STRIKE"] == atm_strike][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s = [''] * len(row)
        try: cur_stk = int(row.iloc[3])
        except: cur_stk = row.iloc[3]
        
        s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold' 
        
        # --- RESISTANCE LINE (BLUE) ---
        if cur_stk == be_res_strike:
            s = ['border-top: 4px solid blue; border-bottom: 4px solid blue; font-weight:bold'] * len(row)
            if spot >= be_res_strike: s = ['background-color: #008000; color: white; font-weight: bold'] * len(row)
        
        # --- SUPPORT LINE (RED) ---
        if cur_stk == be_sup_strike:
            s = ['border-top: 4px solid red; border-bottom: 4px solid red; font-weight:bold'] * len(row)
            if spot <= be_sup_strike: s = ['background-color: #B22222; color: white; font-weight: bold'] * len(row)

        try:
            # Bakki Colors
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            if 'background-color' not in s[0]:
                if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
                if c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
                if c_vo_p >= 70: s[2] = 'background-color:#1b5e20;color:white'
                if p_vo_p >= 70: s[4] = 'background-color:#b71c1c;color:white'
                if p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
                if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'
            
            if cur_stk == int(atm_strike): s[3] = 'background-color:yellow;color:black;font-weight:bold'
        except: pass
        return s

    st.subheader(f"📊 {index_choice} Option Chain")
    st.table(ui.style.apply(style_table, axis=1))
else:
    st.info("Market data load ho raha hai...")
