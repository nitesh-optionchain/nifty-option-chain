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

# ================= 4. SIDEBAR & LOGOUT =================
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
    # Sahi Nifty Price Fetching
    try:
        raw_spot = getattr(result, 'underlying_price', 0)
        if raw_spot == 0:
            raw_spot = getattr(chain.ce[0], 'underlying_price', 0)
        spot = raw_spot / 100 if raw_spot > 50000 else raw_spot
    except: spot = 0

    # Live Nifty Header Card
    prev_close_price = 22450.0 # Standard reference
    nifty_chg = spot - prev_close_price
    nifty_pct = (nifty_chg/prev_close_price)*100
    n_color = "#50fa7b" if nifty_chg >= 0 else "#ff5555"

    st.markdown(f"""
        <div style="background-color:#1e1e2e; padding:15px; border-radius:15px; text-align:center; border: 2px solid {n_color}; margin-bottom: 20px;">
            <p style="color:#a9adc1; margin:0; font-size:14px;">LIVE NIFTY 50 INDEX</p>
            <h1 style="color:{n_color}; margin:0; font-size:38px;">₹ {spot:,.2f} <span style="font-size:18px;">({nifty_chg:+.2f} | {nifty_pct:+.2f}%)</span></h1>
        </div>
    """, unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # Max Values for Calculation
    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()

    # Dynamic OI Change Logic
    if "prev_df" not in st.session_state or st.session_state.prev_df is None:
        st.session_state.prev_df = df.copy()
        df["oi_chg_CE"] = 0
        df["oi_chg_PE"] = 0
    else:
        p_df = st.session_state.prev_df.set_index("STRIKE")
        c_df = df.set_index("STRIKE")
        # Diff calculate kar rahe hain, agar same hai toh purana stored diff use hoga
        df["oi_chg_CE"] = df["STRIKE"].map(lambda x: c_df.loc[x, "open_interest_CE"] - p_df.loc[x, "open_interest_CE"] if x in p_df.index else 0)
        df["oi_chg_PE"] = df["STRIKE"].map(lambda x: c_df.loc[x, "open_interest_PE"] - p_df.loc[x, "open_interest_PE"] if x in p_df.index else 0)

    max_chg_ce = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    max_chg_pe = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    # ================= 6. ADMIN PANEL =================
    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE UI =================
    def fmt(val, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n{pct:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(%)"] = d_df.apply(lambda r: fmt(r["open_interest_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG\n(%)"] = d_df.apply(lambda r: fmt(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_CE"], max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_PE"], max_vol_pe), axis=1)
    ui["PE OI CHG\n(%)"] = d_df.apply(lambda r: fmt(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(%)"] = d_df.apply(lambda r: fmt(r["open_interest_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s = [''] * len(row)
        try:
            # Extract % for each cell
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            # CE Side (Green)
            if c_oi_p >= 100: s[0] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_oi_p >= 70: s[0] = 'background-color:#4caf50;color:white'
            if c_ch_p >= 100: s[1] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
            if c_vo_p >= 70: s[2] = 'background-color:#1976d2;color:white'

            # PE Side (Red)
            if p_vo_p >= 70: s[4] = 'background-color:#e65100;color:white'
            if p_ch_p >= 100: s[5] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
            if p_oi_p >= 100: s[6] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_oi_p >= 70: s[6] = 'background-color:#f44336;color:white'

            if row.iloc[3] >= atm and row.iloc[3] < atm+50: s[3] = 'background-color:yellow;color:black'
        except: pass
        return s

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(style_table, axis=1))
