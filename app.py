from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. PERSISTENT AUTH & CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

# Refresh par logout na ho isliye ye logic sabse upar
if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
if "admin_name" not in st.session_state:
    st.session_state.admin_name = ""
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

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 3. SECURE LOCK =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            u_id = st.text_input("Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if u_id in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[u_id]
                    st.session_state.is_super_admin = (u_id in SUPER_ADMIN_IDS)
                    st.rerun()
                else: st.error("Access Denied")
    st.stop()

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="auto_sync")
st.sidebar.title(f"👤 {st.session_state.admin_name}")
idx_choice = st.sidebar.selectbox("Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if idx_choice == "NIFTY" else "BSE"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

current_data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 5. DATA FETCH & CALCULATION =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

md = MarketData(st.session_state.nubra)
res = md.option_chain(idx_choice, exchange=target_exch)

if res and res.chain:
    c = res.chain
    try:
        raw_spot = getattr(c.ce[0], 'underlying_price', getattr(c, 'underlying_price', 0))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ {idx_choice} ({target_exch}) | Spot: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in c.ce])
    df_pe = pd.DataFrame([vars(x) for x in c.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # OI Change Logic (Stable session base)
    base_key = f"base_{idx_choice}"
    if base_key not in st.session_state:
        st.session_state[base_key] = df.copy()
    
    b_df = st.session_state[base_key].set_index("STRIKE")
    c_df = df.set_index("STRIKE")
    
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: c_df.loc[x, "open_interest_CE"] - b_df.loc[x, "open_interest_CE"] if x in b_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: c_df.loc[x, "open_interest_PE"] - b_df.loc[x, "open_interest_PE"] if x in b_df.index else 0)

    # ================= 6. ADMIN PANEL (MANUAL ENTRY) =================
    if st.session_state.is_super_admin:
        with st.expander("🛠️ ADMIN CONTROL PANEL"):
            c1, c2, c3, c4 = st.columns(4)
            ms = c1.text_input("Strike", current_data["signal"]["Strike"])
            me = c2.text_input("Entry", current_data["signal"]["Entry"])
            mt = c3.text_input("Target", current_data["signal"]["Target"])
            ml = c4.text_input("SL", current_data["signal"]["SL"])
            sup_in = st.text_input("Manual Support", current_data["sr"]["support"])
            res_in = st.text_input("Manual Resistance", current_data["sr"]["resistance"])
            
            if st.button("UPDATE ALL DATA"):
                current_data["signal"] = {"Strike": ms, "Entry": me, "Target": mt, "SL": ml}
                current_data["sr"] = {"support": sup_in, "resistance": res_in}
                save_json(DATA_FILE, current_data)
                st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 STRIKE", current_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_data["signal"]["Entry"])
    m3.metric("🟢 SUPPORT", current_data["sr"]["support"])
    m4.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. ORIGINAL TABLE UI & COLOURS =================
    m_oi_c, m_oi_p = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    m_vol_c, m_vol_p = df["volume_CE"].max(), df["volume_PE"].max()
    m_chg_c = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    m_chg_p = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

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

    def style_table(row):
        s = [''] * len(row)
        try:
            # Parsing percent from string
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white' # Blue
            if c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white' # Green
            if c_vo_p >= 70: s[2] = 'background-color:#1b5e20;color:white' # Dark Green
            if p_vo_p >= 70: s[4] = 'background-color:#b71c1c;color:white' # Dark Red
            if p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white' # Red
            if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white' # Orange
            
            if (row.iloc[3] - spot)**2 < 2500: s[3] = 'background-color:yellow;color:black;font-weight:bold'
        except: pass
        return s

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(style_table, axis=1))
else:
    st.info("Searching for Market Data...")
