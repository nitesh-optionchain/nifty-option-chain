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

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

current_data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 5. SDK & DATA =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")

if result and result.chain:
    chain = result.chain
    # AAPKA ORIGINAL NIFTY LOGIC
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 
                   getattr(chain, 'underlying_price', 
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 50000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | NIFTY: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # STABLE OI CHANGE LOGIC (Current - Initial)
    if "initial_df" not in st.session_state:
        st.session_state.initial_df = df.copy()
    
    init_df = st.session_state.initial_df.set_index("STRIKE")
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_CE"] - init_df.loc[x, "open_interest_CE"] if x in init_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_PE"] - init_df.loc[x, "open_interest_PE"] if x in init_df.index else 0)

    # Max Values
    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    max_chg_pe = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    # ================= 6. ADMIN PANEL =================
    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE UI & STYLING =================
    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    def fmt_chg(delta, m_delta):
        pct = (delta/m_delta*100) if m_delta > 0 else 0
        return f"{delta:+,}\n{pct:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
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
        try:
            # Extract percentages
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            # CE Colors
            if c_oi_p >= 100: s[0] = 'background-color:#0d47a1;color:white;font-weight:bold'
            elif c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
            if c_ch_p >= 100: s[1] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
            if c_vo_p >= 70: s[2] = 'background-color:#1b5e20;color:white'

            # PE Colors
            if p_vo_p >= 70: s[4] = 'background-color:#b71c1c;color:white'
            if p_ch_p >= 100: s[5] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
            if p_oi_p >= 100: s[6] = 'background-color:#e65100;color:white;font-weight:bold'
            elif p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'
            
            # Strike ATM
            if row.iloc[3] == atm: s[3] = 'background-color:yellow;color:black;font-weight:bold'
        except: pass
        return s

    st.subheader("📊 Institutional Option Chain (Stable Data)")
    st.table(ui.style.apply(style_table, axis=1))
