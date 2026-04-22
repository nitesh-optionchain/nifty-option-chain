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

# ================= 4. SIDEBAR & DATA LOAD =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.is_super_admin:
    with st.sidebar.expander("➕ Add New User"):
        n_name = st.text_input("Name")
        n_mob = st.text_input("Mobile")
        if st.button("Authorize"):
            if n_mob and n_name:
                ADMIN_DB[n_mob] = n_name
                save_json(USER_FILE, ADMIN_DB)
                st.sidebar.success("Added!")

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

    # Max Values for Calculations
    max_oi_ce = df["open_interest_CE"].max()
    max_oi_pe = df["open_interest_PE"].max()
    max_vol_ce = df["volume_CE"].max()
    max_vol_pe = df["volume_PE"].max()

    # Change tracking
    if "prev_df" not in st.session_state: st.session_state.prev_df = None
    if st.session_state.prev_df is not None:
        p, c = st.session_state.prev_df.set_index("STRIKE"), df.set_index("STRIKE")
        df["oi_chg_CE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_CE"] - p.loc[x, "open_interest_CE"] if x in p.index else 0).fillna(0)
        df["oi_chg_PE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_PE"] - p.loc[x, "open_interest_PE"] if x in p.index else 0).fillna(0)
    else:
        df["oi_chg_CE"] = df["oi_chg_PE"] = 0
    st.session_state.prev_df = df.copy()

    # Max Change for styling
    max_chg_ce = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    max_chg_pe = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    # ================= 6. ADMIN/VIEWER PANEL =================
    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE STYLING =================
    def format_ui(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    def format_chg_only(delta, m_delta):
        pct = (delta/m_delta*100) if m_delta > 0 else 0
        return f"{delta:+,}\n{pct:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    # CE SIDE
    ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG\n(%)"] = display_df.apply(lambda r: format_chg_only(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_CE"], 0, max_vol_ce), axis=1)
    # MIDDLE
    ui["STRIKE"] = display_df["STRIKE"]
    # PE SIDE
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG\n(%)"] = display_df.apply(lambda r: format_chg_only(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def final_style(row):
        styles = [''] * len(row)
        try:
            ce_oi_pct = float(row.iloc[0].split('\n')[-1].replace('%',''))
            ce_chg_pct = float(row.iloc[1].split('\n')[-1].replace('%',''))
            ce_vol_pct = float(row.iloc[2].split('\n')[-1].replace('%',''))
            pe_vol_pct = float(row.iloc[4].split('\n')[-1].replace('%',''))
            pe_chg_pct = float(row.iloc[5].split('\n')[-1].replace('%',''))
            pe_oi_pct = float(row.iloc[6].split('\n')[-1].replace('%',''))

            # CE Styling
            if ce_oi_pct >= 100: styles[0] = 'background-color:#0d47a1;color:white;font-weight:bold'
            elif ce_oi_pct >= 70: styles[0] = 'background-color:#1976d2;color:white'
            if ce_chg_pct >= 100: styles[1] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif ce_chg_pct >= 70: styles[1] = 'background-color:#4caf50;color:white'
            if ce_vol_pct >= 100: styles[2] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif ce_vol_pct >= 70: styles[2] = 'background-color:#4caf50;color:white'

            # PE Styling
            if pe_vol_pct >= 100: styles[4] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif pe_vol_pct >= 70: styles[4] = 'background-color:#f44336;color:white'
            if pe_chg_pct >= 100: styles[5] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif pe_chg_pct >= 70: styles[5] = 'background-color:#f44336;color:white'
            if pe_oi_pct >= 100: styles[6] = 'background-color:#e65100;color:white;font-weight:bold'
            elif pe_oi_pct >= 70: styles[6] = 'background-color:#fb8c00;color:white'
            
            # Strike ATM
            if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
            else: styles[3] = 'background-color:#eeeeee'
        except: pass
        return styles

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(final_style, axis=1))
