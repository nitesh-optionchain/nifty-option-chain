from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. STRICT AUTH CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# Persistent Session Initialization
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
if "admin_name" not in st.session_state:
    st.session_state.admin_name = None
if "is_super_admin" not in st.session_state:
    st.session_state.is_super_admin = False

# ================= 2. DATA STORAGE =================
DATA_FILE = "admin_data.json"
USER_FILE = "authorized_users.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f:
            json.dump(data_to_save, f)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 3. THE "LOCK" (LOGIN SCREEN) =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Please login to access the Private Dashboard</p>", unsafe_allow_html=True)
    
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Strict_Login"):
            user_key = st.text_input("Enter Authorized Mobile ID:", type="password")
            if st.form_submit_button("UNLOCK DASHBOARD"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.is_super_admin = (user_key in SUPER_ADMIN_IDS)
                    st.rerun()
                else:
                    st.error("❌ Access Denied: Unauthorized ID")
    # Yahan stop() laga hai, iske niche ka code bina login ke kabhi run nahi hoga
    st.stop()

# ================= 4. DASHBOARD (ONLY FOR AUTH USERS) =================
st_autorefresh(interval=5000, key="live_refresh")

# Sidebar
st.sidebar.success(f"🔓 Connected: {st.session_state.admin_name}")
index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("🔒 SECURE LOGOUT"):
    st.session_state.is_auth = False
    st.session_state.admin_name = None
    st.rerun()

current_data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 5. DATA FETCHING =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 
                   getattr(chain, 'underlying_price', 
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ {index_choice} | {target_exch} | Spot: {spot:,.2f}")

    # OI Change Logic
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    state_key = f"base_df_{index_choice}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()
    
    base_df = st.session_state[state_key].set_index("STRIKE")
    df_curr = df.set_index("STRIKE")
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: df_curr.loc[x, "open_interest_CE"] - base_df.loc[x, "open_interest_CE"] if x in base_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: df_curr.loc[x, "open_interest_PE"] - base_df.loc[x, "open_interest_PE"] if x in base_df.index else 0)

    # Max Vals for Styling
    m_oi_c, m_oi_p = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    m_vol_c, m_vol_p = df["volume_CE"].max(), df["volume_PE"].max()
    m_chg_c, m_chg_p = df["oi_chg_CE"].abs().max(), df["oi_chg_PE"].abs().max()

    # ================= 6. ADMIN PANEL (MANUAL S/R) =================
    if st.session_state.is_super_admin:
        with st.expander("🎯 ADMIN CONTROLS (Signals & Levels)"):
            s_sup_in = st.text_input("Manual Support", value=current_data["sr"]["support"])
            s_res_in = st.text_input("Manual Resistance", value=current_data["sr"]["resistance"])
            if st.button("UPDATE DASHBOARD LEVELS"):
                current_data["sr"] = {"support": s_sup_in, "resistance": s_res_in}
                save_json(DATA_FILE, current_data)
                st.rerun()

    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. STYLED TABLE =================
    def fmt(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100 if m>0 else 0):.1f}%"
    def fmt_chg(d, m): return f"{d:+,}\n{(d/m*100 if m>0 else 0):.1f}%"

    atm_idx = (df['STRIKE'] - spot).abs().idxmin()
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], m_oi_c), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_CE"], m_chg_c), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_CE"], 0, m_vol_c), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_PE"], 0, m_vol_p), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_PE"], m_chg_p), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], m_oi_p), axis=1)

    def style_ui(row):
        s = [''] * len(row)
        try:
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            if c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
            if p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
            if (row.iloc[3] - spot)**2 < 2500: s[3] = 'background-color:yellow;color:black;font-weight:bold'
        except: pass
        return s

    st.table(ui.style.apply(style_ui, axis=1))
else:
    st.info("Awaiting Market Data...")
