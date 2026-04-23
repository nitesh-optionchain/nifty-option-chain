from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & AUTH =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
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

def save_json(file_path, data):
    with open(file_path, "w") as f: json.dump(data, f)

# Authorized Users Load
ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 3. SECURE LOGIN =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("SecureLogin"):
            u_key = st.text_input("Mobile ID:", type="password")
            if st.form_submit_button("UNLOCK"):
                if u_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[u_key]
                    st.session_state.is_super_admin = (u_key in SUPER_ADMIN_IDS)
                    st.rerun()
                else: st.error("Unauthorized!")
    st.stop()

# ================= 4. SIDEBAR & TOOLS =================
st_autorefresh(interval=5000, key="refresh_sync")
st.sidebar.title(f"👤 {st.session_state.admin_name}")
idx_choice = st.sidebar.selectbox("Index", ["NIFTY", "SENSEX"])
exch = "NSE" if idx_choice == "NIFTY" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

current_data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 5. DATA FETCH & OI LOGIC =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

md = MarketData(st.session_state.nubra)
res = md.option_chain(idx_choice, exchange=exch)

if res and res.chain:
    c = res.chain
    try:
        raw_spot = getattr(c.ce[0], 'underlying_price', getattr(c, 'underlying_price', 0))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    df_ce = pd.DataFrame([vars(x) for x in c.ce])
    df_pe = pd.DataFrame([vars(x) for x in c.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # STABLE OI CHANGE: Current OI - Previous Close OI
    # previous_close_oi column SDK provide karta hai, agar nahi toh 0 lega
    df["oi_chg_CE"] = df["open_interest_CE"] - df.get("previous_close_oi_CE", df["open_interest_CE"])
    df["oi_chg_PE"] = df["open_interest_PE"] - df.get("previous_close_oi_PE", df["open_interest_PE"])

    # ================= 6. ADMIN PANEL =================
    if st.session_state.is_super_admin:
        with st.expander("🛠️ ADMIN CONTROL PANEL"):
            tab1, tab2 = st.tabs(["Signal/Levels", "User Management"])
            with tab1:
                c1, c2, c3, c4 = st.columns(4)
                stk = c1.text_input("Strike", current_data["signal"]["Strike"])
                ent = c2.text_input("Entry", current_data["signal"]["Entry"])
                tgt = c3.text_input("Target", current_data["signal"]["Target"])
                sl = c4.text_input("SL", current_data["signal"]["SL"])
                sup = st.text_input("Support", current_data["sr"]["support"])
                res_lvl = st.text_input("Resistance", current_data["sr"]["resistance"])
                if st.button("SAVE ALL DATA"):
                    current_data["signal"] = {"Strike": stk, "Entry": ent, "Target": tgt, "SL": sl}
                    current_data["sr"] = {"support": sup, "resistance": res_lvl}
                    save_json(DATA_FILE, current_data)
                    st.rerun()
            with tab2:
                new_no = st.text_input("Add Mobile Number")
                new_name = st.text_input("User Name")
                if st.button("ADD USER"):
                    ADMIN_DB[new_no] = new_name
                    save_json(USER_FILE, ADMIN_DB)
                    st.success("User Added!")

    # Display Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 STRIKE", current_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_data["signal"]["Entry"])
    m3.metric("🟢 SUP", current_data["sr"]["support"])
    m4.metric("🔴 RES", current_data["sr"]["resistance"])

    # ================= 7. TABLE UI & COLOURS =================
    m_oi_c, m_oi_p = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    m_vol_c, m_vol_p = df["volume_CE"].max(), df["volume_PE"].max()
    
    def fmt(v, d, m): 
        p = (v/m*100) if m > 0 else 0
        return f"{v:,.0f}\n({d:+,})\n{p:.1f}%"

    atm_idx = (df['STRIKE'] - spot).abs().idxmin()
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], m_oi_c), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_CE"], 0, m_vol_c), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt(r["volume_PE"], 0, m_vol_p), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], m_oi_p), axis=1)

    def style(row):
        s = [''] * len(row)
        try:
            c_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            p_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            if c_p >= 70: s[0] = 'background-color:#1976d2;color:white' # Blue
            if p_p >= 70: s[4] = 'background-color:#fb8c00;color:white' # Orange
            if (row.iloc[2] - spot)**2 < 2500: s[2] = 'background-color:yellow;color:black' # ATM
        except: pass
        return s

    st.table(ui.style.apply(style, axis=1))
else:
    st.info("Fetching Market Data...")
