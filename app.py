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

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
    "sr": {"support": "-", "resistance": "-"}
})

# Admin Database Load
ADMIN_DB = load_json(USER_FILE, {
    "9304768496": "Admin Chief", 
    "7982046438": "Admin X"
})

# Yahan aap un IDs ko daalein jo edit kar sakte hain
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
                    # Check if user is Super Admin
                    st.session_state.is_super_admin = True if user_key in SUPER_ADMIN_IDS else False
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SIDEBAR =================
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
role = "MAIN ADMIN" if st.session_state.is_super_admin else "VIEW ONLY"
st.sidebar.info(f"Access Level: {role}")

# Add New Admin option sirf Main Admins ko dikhega
if st.session_state.is_super_admin:
    with st.sidebar.expander("➕ Add New User"):
        new_name = st.text_input("Name")
        new_mobile = st.text_input("Mobile Number")
        if st.button("Authorize"):
            if new_mobile and new_name:
                ADMIN_DB[new_mobile] = new_name
                save_json(USER_FILE, ADMIN_DB)
                st.sidebar.success(f"Added {new_name}")
            else: st.sidebar.error("Fill both fields")

if st.sidebar.button("Logout"):
    st.session_state.is_auth = False
    st.rerun()

# ================= 5. SDK & DATA FETCH =================
st_autorefresh(interval=5000, key="refresh")

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

    # Data Processing
    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # Change Logic
    if "prev_df" not in st.session_state: st.session_state.prev_df = None
    if st.session_state.prev_df is not None:
        p, c = st.session_state.prev_df.set_index("STRIKE"), df.set_index("STRIKE")
        df["oi_chg_CE"] = df["STRIKE"].map(c["open_interest_CE"] - p["open_interest_CE"]).fillna(0)
        df["oi_chg_PE"] = df["STRIKE"].map(c["open_interest_PE"] - p["open_interest_PE"]).fillna(0)
        df["prc_chg_CE"] = df["STRIKE"].map(c["last_traded_price_CE"] - p["last_traded_price_CE"]).fillna(0)
        df["prc_chg_PE"] = df["STRIKE"].map(c["last_traded_price_PE"] - p["last_traded_price_PE"]).fillna(0)
    else:
        df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0
    st.session_state.prev_df = df.copy()

    # ================= 6. SIGNALS & S/R (ROLE BASED) =================
    st.markdown("---")
    
    if st.session_state.is_super_admin:
        # Edit Mode for Main Admins
        st.subheader("🎯 UPDATE TRADE SIGNALS")
        c1, c2, c3, c4, c5 = st.columns(5)
        s_stk = c1.text_input("Strike", value=data["signal"]["Strike"])
        s_ent = c2.text_input("Entry", value=data["signal"]["Entry"])
        s_tgt = c3.text_input("Target", value=data["signal"]["Target"])
        s_sl = c4.text_input("SL", value=data["signal"]["SL"])
        if c5.button("📢 UPDATE"):
            data["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl, "Status": f"LIVE ({st.session_state.admin_name})"}
            save_json(DATA_FILE, data)
            st.rerun()

        st.subheader("📊 UPDATE S/R LEVELS")
        s1, s2, s3 = st.columns(3)
        m_sup = s1.text_input("Support", data["sr"]["support"])
        m_res = s2.text_input("Resistance", data["sr"]["resistance"])
        if s3.button("SET LEVELS"):
            data["sr"] = {"support": m_sup, "resistance": m_res}
            save_json(DATA_FILE, data)
            st.rerun()
    else:
        # Display Mode for View-Only Admins
        st.subheader("🎯 CURRENT TRADE SIGNALS")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Strike", data["signal"]["Strike"])
        m2.metric("Entry", data["signal"]["Entry"])
        m3.metric("Target", data["signal"]["Target"])
        m4.metric("SL", data["signal"]["SL"])
        m5.metric("Status", data["signal"]["Status"])

    # Live S/R Metrics
    a, b = st.columns(2)
    a.metric("🟢 SUPPORT", data["sr"]["support"])
    b.metric("🔴 RESISTANCE", data["sr"]["resistance"])

    # ================= 7. TABLE STYLING =================
    def format_ui(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    def get_buildup(p, o):
        if p > 0 and o > 0: return "🟢 LONG"
        if p < 0 and o > 0: return "🔴 SHORT"
        return "⚪ -"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"] >= atm][0]
    display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE BUILDUP"] = display_df.apply(lambda r: get_buildup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
    ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
    ui["STRIKE"] = display_df["STRIKE"]
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
    ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)
    ui["PE BUILDUP"] = display_df.apply(lambda r: get_buildup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

    def final_style(row):
        styles = [''] * len(row)
        try:
            ce_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
            ce_vol = float(row.iloc[2].split('\n')[-1].replace('%',''))
            pe_vol = float(row.iloc[4].split('\n')[-1].replace('%',''))
            pe_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))

            if ce_oi > 65: styles[1] = 'background-color:#0d47a1;color:white;font-weight:bold'
            if ce_vol >= 90: styles[2] = 'background-color:#00c853;color:white;font-weight:bold'
            if pe_oi > 65: styles[5] = 'background-color:#ff6f00;color:white;font-weight:bold'
            if pe_vol >= 90: styles[4] = 'background-color:#d50000;color:white;font-weight:bold'
            
            if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
            else: styles[3] = 'background-color:#eeeeee'
        except: pass
        return styles

    st.subheader("📊 Institutional Option Chain")
    st.table(ui.style.apply(final_style, axis=1))
else:
    st.info("Market data is loading...")
