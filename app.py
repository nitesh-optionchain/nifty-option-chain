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

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "9822334455": "Amit Kumar"})
SUPER_ADMIN_IDS = ["9304768496", "9822334455"]

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
    # Sahi Spot Price fetch karne ka logic
    raw_spot = getattr(result, 'underlying_price', 0)
    if raw_spot == 0:
        raw_spot = getattr(chain, 'underlying_price', 0)
    spot = raw_spot / 100 if raw_spot > 50000 else raw_spot

    # Live Nifty Box
    st.markdown(f"""
        <div style="background-color:#1e1e2e; padding:15px; border-radius:15px; text-align:center; border: 2px solid #50fa7b; margin-bottom: 20px;">
            <p style="color:#a9adc1; margin:0; font-size:16px;">LIVE NIFTY 50</p>
            <h1 style="color:#50fa7b; margin:0; font-size:42px;">₹ {spot:,.2f}</h1>
        </div>
    """, unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # OI Change Logic (Using SDK provided change or calculating from session)
    if "prev_df" not in st.session_state: st.session_state.prev_df = None
    if st.session_state.prev_df is not None:
        p, c = st.session_state.prev_df.set_index("STRIKE"), df.set_index("STRIKE")
        df["oi_chg_CE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_CE"] - p.loc[x, "open_interest_CE"] if x in p.index else 0)
        df["oi_chg_PE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_PE"] - p.loc[x, "open_interest_PE"] if x in p.index else 0)
    else:
        # Initial Load: using 5% of OI as placeholder until next refresh
        df["oi_chg_CE"] = df["open_interest_CE"] * 0.05
        df["oi_chg_PE"] = df["open_interest_PE"] * 0.05
    st.session_state.prev_df = df.copy()

    # Max Values for Colors
    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce, max_chg_pe = df["oi_chg_CE"].abs().max(), df["oi_chg_PE"].abs().max()

    # ================= 6. ADMIN PANEL =================
    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE FORMATTING =================
    def format_row(val, delta, m_delta):
        pct = (delta/m_delta*100) if m_delta > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_row(r["open_interest_CE"], r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: f"{r['volume_CE']:,.0f}\n{(r['volume_CE']/max_vol_ce*100 if max_vol_ce>0 else 0):.1f}%", axis=1)
    ui["STRIKE"] = display_df["STRIKE"]
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: f"{r['volume_PE']:,.0f}\n{(r['volume_PE']/max_vol_pe*100 if max_vol_pe>0 else 0):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_row(r["open_interest_PE"], r["oi_chg_PE"], max_chg_pe), axis=1)

    def style_logic(row):
        styles = [''] * len(row)
        try:
            ce_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            ce_vo_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            pe_vo_p = float(row.iloc[3].split('\n')[-1].replace('%',''))
            pe_oi_p = float(row.iloc[4].split('\n')[-1].replace('%',''))

            # CE Color (Green)
            if ce_oi_p >= 100: styles[0] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif ce_oi_p >= 70: styles[0] = 'background-color:#4caf50;color:white'
            if ce_vo_p >= 70: styles[1] = 'background-color:#0d47a1;color:white'

            # PE Color (Red)
            if pe_oi_p >= 100: styles[4] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif pe_oi_p >= 70: styles[4] = 'background-color:#f44336;color:white'
            if pe_vo_p >= 70: styles[3] = 'background-color:#e65100;color:white'
            
            # Strike
            if row.iloc[2] >= atm and row.iloc[2] < atm + 50: styles[2] = 'background-color:yellow;color:black'
        except: pass
        return styles

    st.subheader("📊 Institutional Option Chain (Live OI Change)")
    st.table(ui.style.apply(style_logic, axis=1))
