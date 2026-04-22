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

    # Max Change Values for Relative % Colour Logic
    max_chg_ce = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    max_chg_pe = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    # ================= 6. ADMIN/VIEWER PANEL =================
    st.markdown("---")
    if st.session_state.is_super_admin:
        st.subheader("🎯 UPDATE SIGNALS")
        c1, c2, c3, c4, c5 = st.columns(5)
        s_stk = c1.text_input("Strike", value=current_data["signal"]["Strike"])
        s_ent = c2.text_input("Entry", value=current_data["signal"]["Entry"])
        s_tgt = c3.text_input("Target", value=current_data["signal"]["Target"])
        s_sl = c4.text_input("SL", value=current_data["signal"]["SL"])
        if c5.button("📢 UPDATE"):
            current_data["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl, "Status": f"LIVE ({st.session_state.admin_name})"}
            save_json(DATA_FILE, current_data)
            st.rerun()
        
        s1, s2, s3 = st.columns(3)
        m_sup = s1.text_input("Support", current_data["sr"]["support"])
        m_res = s2.text_input("Resistance", current_data["sr"]["resistance"])
        if s3.button("SET LEVELS"):
            current_data["sr"] = {"support": m_sup, "resistance": m_res}
            save_json(DATA_FILE, current_data)
            st.rerun()
    else:
        st.subheader("🎯 LIVE TRADE SIGNALS")
        v1, v2, v3, v4, v5 = st.columns(5)
        v1.metric("Strike", current_data["signal"]["Strike"])
        v2.metric("Entry", current_data["signal"]["Entry"])
        v3.metric("Target", current_data["signal"]["Target"])
        v4.metric("SL", current_data["signal"]["SL"])
        v5.metric("Status", current_data["signal"]["Status"])

    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE STYLING =================
    def format_ui(val, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n{pct:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    # CE Side
    ui["CE OI\n(%)"] = display_df.apply(lambda r: format_ui(r["open_interest_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG\n(%)"] = display_df.apply(lambda r: format_ui(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_CE"], max_vol_ce), axis=1)
    # Middle
    ui["STRIKE"] = display_df["STRIKE"]
    # PE Side
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_PE"], max_vol_pe), axis=1)
    ui["PE OI CHG\n(%)"] = display_df.apply(lambda r: format_ui(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(%)"] = display_df.apply(lambda r: format_ui(r["open_interest_PE"], max_oi_pe), axis=1)

    def final_style(row):
        styles = [''] * len(row)
        try:
            # Pct Extraction for all columns
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            # CE Colours (Blue/Green)
            if c_oi_p >= 100: styles[0] = 'background-color:#0d47a1;color:white;font-weight:bold'
            elif c_oi_p >= 70: styles[0] = 'background-color:#1976d2;color:white'
            
            if c_ch_p >= 100: styles[1] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_ch_p >= 70: styles[1] = 'background-color:#4caf50;color:white'
            
            if c_vo_p >= 100: styles[2] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_vo_p >= 70: styles[2] = 'background-color:#4caf50;color:white'

            # PE Colours (Red/Orange)
            if p_vo_p >= 100: styles[4] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_vo_p >= 70: styles[4] = 'background-color:#f44336;color:white'
            
            if p_ch_p >= 100: styles[5] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_ch_p >= 70: styles[5] = 'background-color:#f44336;color:white'

            if p_oi_p >= 100: styles[6] = 'background-color:#e65100;color:white;font-weight:bold'
            elif p_oi_p >= 70: styles[6] = 'background-color:#fb8c00;color:white'
            
            # Strike Price
            if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
            else: styles[3] = 'background-color:#eeeeee'
        except: pass
        return styles

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(final_style, axis=1))
