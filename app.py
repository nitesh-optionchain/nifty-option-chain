from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
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

# ================= 4. SIDEBAR & DYNAMIC DATA =================
st_autorefresh(interval=5000, key="refresh")
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. SDK & DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

md = MarketData(st.session_state.nubra)
res = md.option_chain(index_choice, exchange=target_exch)

if res and res.chain:
    c = res.chain
    try:
        raw_spot = getattr(c.ce[0], 'underlying_price', getattr(c, 'underlying_price', 0))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce, df_pe = pd.DataFrame([vars(x) for x in c.ce]), pd.DataFrame([vars(x) for x in c.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # OI Change Stable Logic
    state_key = f"init_{index_choice}"
    if state_key not in st.session_state: st.session_state[state_key] = df.copy()
    init_df = st.session_state[state_key].set_index("STRIKE")
    
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_CE"] - init_df.loc[x, "open_interest_CE"] if x in init_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_PE"] - init_df.loc[x, "open_interest_PE"] if x in init_df.index else 0)

    # Max Values for Calculations
    m_oi_c, m_oi_p = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    m_vol_c, m_vol_p = df["volume_CE"].max(), df["volume_PE"].max()
    m_chg_c, m_chg_p = df["oi_chg_CE"].abs().max() or 1, df["oi_chg_PE"].abs().max() or 1

    # ================= 6. AUTO SIGNAL ENGINE =================
    # Break-Even Point: Jahan OI Build-up sabse tagda hai
    be_resistance = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
    be_support = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

    # Scalping Signal
    ce_power = (df["oi_chg_CE"].max() / m_chg_c * 100)
    pe_power = (df["oi_chg_PE"].max() / m_chg_p * 100)
    
    if ce_power > 80 and spot > be_resistance:
        st.error(f"🚀 BIG MOVE ALERT: CALL SIDE BREAKOUT ABOVE {be_resistance}")
    elif pe_power > 80 and spot < be_support:
        st.warning(f"📉 BIG MOVE ALERT: PUT SIDE BREAKDOWN BELOW {be_support}")

    # ================= 7. TABLE UI & BIG MOVE LINE =================
    def fmt(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100 if m>0 else 0):.1f}%"
    def fmt_c(d, m): return f"{d:+,}\n{(d/m*100 if m>0 else 0):.1f}%"

    atm_idx = df.index[(df["STRIKE"] - spot).abs().argsort()[:1]][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], m_oi_c), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_c(r["oi_chg_CE"], m_chg_c), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_CE"], 0, m_vol_c), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_PE"], 0, m_vol_p), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_c(r["oi_chg_PE"], m_chg_p), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], m_oi_p), axis=1)

    def style_table(row):
        s = [''] * len(row)
        s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold'
        
        strike = row.iloc[3]
        # LONG LINE SIGNAL (Break-Even Border)
        if strike == be_resistance:
            s = ['border-top: 4px solid #0d47a1; border-bottom: 4px solid #0d47a1; font-weight:bold'] * len(row)
        if strike == be_support:
            s = ['border-top: 4px solid #b71c1c; border-bottom: 4px solid #b71c1c; font-weight:bold'] * len(row)

        try:
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))
            
            if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
            if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'
            if strike == atm_idx: s[3] = 'background-color:yellow;color:black'
        except: pass
        return s

    # Manual Metrics Display
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 STRIKE", current_idx_data["signal"]["Strike"])
    c2.metric("💰 ENTRY", current_idx_data["signal"]["Entry"])
    c3.metric("🟢 SUP", current_idx_data["sr"]["support"])
    c4.metric("🔴 RES", current_idx_data["sr"]["resistance"])

    st.table(ui.style.apply(style_table, axis=1))

    # Admin Panel (Dynamic)
    if st.session_state.is_super_admin:
        with st.expander("🛠️ DYNAMIC ADMIN SETTINGS"):
            sc1, sc2, sc3, sc4 = st.columns(4)
            ms = sc1.text_input("Strike", current_idx_data["signal"]["Strike"])
            me = sc2.text_input("Entry", current_idx_data["signal"]["Entry"])
            ss = st.text_input("Support", current_idx_data["sr"]["support"])
            sr = st.text_input("Resistance", current_idx_data["sr"]["resistance"])
            if st.button(f"SAVE {index_choice} DATA"):
                all_index_data[index_choice]["signal"].update({"Strike": ms, "Entry": me})
                all_index_data[index_choice]["sr"].update({"support": ss, "resistance": sr})
                save_json(DATA_FILE, all_index_data)
                st.rerun()
