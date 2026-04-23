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

# TradingView Symbol Logic
tv_symbol = "NSE:NIFTY" if index_choice == "NIFTY" else "BSE:SENSEX"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. TRADINGVIEW HEADER WIDGET =================
st.markdown("---")
tv_html = f"""
<div class="tradingview-widget-container">
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
  {{
  "symbol": "{tv_symbol}",
  "width": "100%",
  "colorTheme": "light",
  "isTransparent": false,
  "locale": "en"
  }}
  </script>
</div>
"""
components.html(tv_html, height=130)

# ================= 6. SDK & STABLE DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', getattr(chain, 'underlying_price', 0))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.subheader(f"🛡️ LIVE {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()

    def calc_stable_oi(row, side):
        curr_oi = row[f"open_interest_{side}"]
        prev_oi = row.get(f"previous_close_oi_{side}", 0)
        if prev_oi == 0:
            init_df = st.session_state[state_key].set_index("STRIKE")
            strike = row["STRIKE"]
            if strike in init_df.index:
                prev_oi = init_df.loc[strike, f"open_interest_{side}"]
        return curr_oi - prev_oi

    df["oi_chg_CE"] = df.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
    df["oi_chg_PE"] = df.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce, max_chg_pe = df["oi_chg_CE"].abs().max() or 1, df["oi_chg_PE"].abs().max() or 1

    # Break-Even Strikes
    be_res_strike = int(df.loc[df["open_interest_CE"].idxmax(), "STRIKE"])
    be_sup_strike = int(df.loc[df["open_interest_PE"].idxmax(), "STRIKE"])

    # Auto Signal Alert (Pure Header Logic)
    if spot >= be_res_strike:
        st.success(f"🚀 BIG MOVE ALERT: {index_choice} CALL BREAKOUT ABOVE {be_res_strike}")
    elif spot <= be_sup_strike:
        st.error(f"🩸 BIG MOVE ALERT: {index_choice} PUT BREAKDOWN BELOW {be_sup_strike}")

    # Top Metrics Structure
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🎯 STRIKE", current_idx_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_idx_data["signal"]["Entry"])
    m3.metric("📈 TARGET", current_idx_data["signal"]["Target"])
    m4.metric("📉 SL", current_idx_data["signal"]["SL"])
    m5.metric("🟢 SUP", current_idx_data["sr"]["support"])
    m6.metric("🔴 RES", current_idx_data["sr"]["resistance"])

    # ================= 7. TABLE UI & STYLING =================
    def fmt_val(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100 if m>0 else 0):.1f}%"
    def fmt_chg(d, m): return f"{d:+,}\n{(d/m*100 if m>0 else 0):.1f}%"

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
        try: cur_strike = int(float(row.iloc[3]))
        except: cur_strike = row.iloc[3]
        
        s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold' 

        # Break-Even & Big Move Line Styling
        if cur_strike == be_res_strike:
            s = ['border-top: 3px solid blue; border-bottom: 3px solid blue; font-weight:bold'] * len(row)
            if spot >= be_res_strike: s = ['background-color: #008000; color: white; border: 2px solid white'] * len(row)
        
        if cur_strike == be_sup_strike:
            s = ['border-top: 3px solid red; border-bottom: 3px solid red; font-weight:bold'] * len(row)
            if spot <= be_sup_strike: s = ['background-color: #FF0000; color: white; border: 2px solid white'] * len(row)

        try:
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))
            if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
            if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'
            if cur_strike == int(atm_strike): s[3] = 'background-color:yellow;color:black'
        except: pass
        return s

    st.table(ui.style.apply(style_table, axis=1))

    # Admin Panel
    if st.session_state.is_super_admin:
        with st.expander("🛠️ ADMIN CONTROLS"):
            t1, t2 = st.tabs(["Signals", "Users"])
            with t1:
                c1, c2, c3, c4 = st.columns(4)
                s_stk = c1.text_input("Strike", value=current_idx_data["signal"]["Strike"])
                s_ent = c2.text_input("Entry", value=current_idx_data["signal"]["Entry"])
                s_tgt = c3.text_input("Target", value=current_idx_data["signal"]["Target"])
                s_sl = c4.text_input("SL", value=current_idx_data["signal"]["SL"])
                su_i = st.text_input("Support", value=current_idx_data["sr"]["support"])
                re_i = st.text_input("Resistance", value=current_idx_data["sr"]["resistance"])
                if st.button(f"UPDATE {index_choice}"):
                    all_index_data[index_choice]["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl}
                    all_index_data[index_choice]["sr"] = {"support": su_i, "resistance": re_i}
                    save_json(DATA_FILE, all_index_data)
                    st.rerun()
            with t2:
                n_id = st.text_input("Mobile ID")
                if st.button("ADD USER"):
                    ADMIN_DB[n_id] = "Authorized Admin"
                    save_json(USER_FILE, ADMIN_DB)
                    st.success("User Added!")
