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

if st.session_state.is_super_admin:
    with st.sidebar.expander("➕ Add New User"):
        n_name = st.text_input("Name")
        n_mob = st.text_input("Mobile")
        if st.button("Authorize"):
            if n_mob and n_name:
                ADMIN_DB[n_mob] = n_name
                save_json(USER_FILE, ADMIN_DB)
                st.sidebar.success("Added!")

st.sidebar.markdown("---")
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
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 
                   getattr(chain, 'underlying_price', 
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 50000 else raw_spot
    except: spot = 0

    # Live Header Box with Change Logic
    prev_close = 22450 # Example, should ideally come from SDK
    day_chg = spot - prev_close
    chg_pct = (day_chg / prev_close) * 100
    color = "#50fa7b" if day_chg >= 0 else "#ff5555"
    icon = "▲" if day_chg >= 0 else "▼"

    st.markdown(f"""
        <div style="background-color:#1e1e2e; padding:15px; border-radius:15px; text-align:center; border: 2px solid {color}; margin-bottom: 20px;">
            <p style="color:#a9adc1; margin:0; font-size:16px;">NIFTY 50 INDEX</p>
            <h1 style="color:{color}; margin:0; font-size:42px;">₹ {spot:,.2f} <span style="font-size:20px;">{icon} {day_chg:+.2f} ({chg_pct:+.2f}%)</span></h1>
        </div>
    """, unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # OI Change tracking
    if "prev_df" not in st.session_state: st.session_state.prev_df = None
    if st.session_state.prev_df is not None:
        p, c = st.session_state.prev_df.set_index("STRIKE"), df.set_index("STRIKE")
        df["oi_chg_CE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_CE"] - p.loc[x, "open_interest_CE"] if x in p.index else 0)
        df["oi_chg_PE"] = df["STRIKE"].map(lambda x: c.loc[x, "open_interest_PE"] - p.loc[x, "open_interest_PE"] if x in p.index else 0)
    else:
        df["oi_chg_CE"] = df["oi_chg_PE"] = 0
    st.session_state.prev_df = df.copy()

    # Max values for logic
    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce, max_chg_pe = df["oi_chg_CE"].abs().max(), df["oi_chg_PE"].abs().max()

    # ================= 6. ADMIN/SIGNALS =================
    if st.session_state.is_super_admin:
        st.subheader("🎯 UPDATE SIGNALS")
        c1, c2, c3, c4, c5 = st.columns(5)
        s_stk = c1.text_input("Strike", value=current_data["signal"]["Strike"])
        s_ent = c2.text_input("Entry", value=current_data["signal"]["Entry"])
        s_tgt = c3.text_input("Target", value=current_data["signal"]["Target"])
        s_sl = c4.text_input("SL", value=current_data["signal"]["SL"])
        if c5.button("📢 UPDATE"):
            current_data["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl, "Status": "LIVE"}
            save_json(DATA_FILE, current_data)
            st.rerun()

    ma, mb = st.columns(2)
    ma.metric("🟢 SUPPORT", current_data["sr"]["support"])
    mb.metric("🔴 RESISTANCE", current_data["sr"]["resistance"])

    # ================= 7. TABLE FORMATTING =================
    def fmt(val, delta, m_val):
        p = (delta/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: f"{r['volume_CE']:,.0f}\n{(r['volume_CE']/max_vol_ce*100 if max_vol_ce>0 else 0):.1f}%", axis=1)
    ui["STRIKE"] = display_df["STRIKE"]
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: f"{r['volume_PE']:,.0f}\n{(r['volume_PE']/max_vol_pe*100 if max_vol_pe>0 else 0):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], max_chg_pe), axis=1)

    def final_style(row):
        styles = [''] * len(row)
        try:
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            p_vo_p = float(row.iloc[3].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[4].split('\n')[-1].replace('%',''))

            # CE Side: Green
            if c_oi_p >= 100: styles[0] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_oi_p >= 70: styles[0] = 'background-color:#4caf50;color:white'
            if c_vo_p >= 100: styles[1] = 'background-color:#1b5e20;color:white;font-weight:bold'
            elif c_vo_p >= 70: styles[1] = 'background-color:#4caf50;color:white'

            # PE Side: Red
            if p_oi_p >= 100: styles[4] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_oi_p >= 70: styles[4] = 'background-color:#f44336;color:white'
            if p_vo_p >= 100: styles[3] = 'background-color:#b71c1c;color:white;font-weight:bold'
            elif p_vo_p >= 70: styles[3] = 'background-color:#f44336;color:white'

            if row.iloc[2] >= atm and row.iloc[2] < atm+50: styles[2] = 'background-color:yellow;color:black'
        except: pass
        return styles

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(final_style, axis=1))
