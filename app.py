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
DATA_FILE = "admin_data_v2.json"
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

# ================= 3. LOGIN =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1,1,1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.is_super_admin = user_key in SUPER_ADMIN_IDS
                    st.rerun()
                else:
                    st.error("❌ Invalid ID")
    st.stop()

# ================= 4. SIDEBAR =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"👤 {st.session_state.admin_name}")

index_choice = st.sidebar.selectbox("Index", ["NIFTY","SENSEX"])
target_exch = "NSE" if index_choice=="NIFTY" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

# ================= 5. DATA =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:

    chain = result.chain

    try:
        raw_spot = chain.ce[0].underlying_price
        spot = raw_spot/100
    except:
        spot = chain.at_the_money_strike/100

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])

    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    df["oi_chg_CE"] = df["open_interest_CE"].diff().fillna(0)
    df["oi_chg_PE"] = df["open_interest_PE"].diff().fillna(0)

    max_oi_ce = df["open_interest_CE"].max()
    max_oi_pe = df["open_interest_PE"].max()
    max_vol_ce = df["volume_CE"].max()
    max_vol_pe = df["volume_PE"].max()

    # ================= BREAK EVEN =================
    total_ce = df["open_interest_CE"].sum()
    total_pe = df["open_interest_PE"].sum()

    be_strike = int(df.loc[(df["open_interest_CE"]+df["open_interest_PE"]).idxmax(),"STRIKE"])

    signal_type = None
    if total_pe > total_ce:
        signal_type = "CALL"
    elif total_ce > total_pe:
        signal_type = "PUT"

    # ================= TABLE =================
    def format_val(val, delta, m):
        p = (val/m*100) if m>0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

    atm = int(spot)
    atm_idx = df.index[df["STRIKE"]>=atm][0]
    display_df = df.iloc[max(atm_idx-7,0):atm_idx+8].copy()

    ui = pd.DataFrame()

    ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = display_df.apply(lambda r: format_val(r["oi_chg_CE"],0,max_oi_ce), axis=1)
    ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"],0,max_vol_ce), axis=1)
    ui["STRIKE"] = display_df["STRIKE"]
    ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"],0,max_vol_pe), axis=1)
    ui["PE OI CHG"] = display_df.apply(lambda r: format_val(r["oi_chg_PE"],0,max_oi_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    # SIGNAL
    ui["SIGNAL"] = ""

    for i in range(len(ui)):
        if ui.iloc[i]["STRIKE"] == be_strike:
            if signal_type == "CALL":
                ui.at[ui.index[i],"SIGNAL"] = "⬆️ CALL BUY"
            elif signal_type == "PUT":
                ui.at[ui.index[i],"SIGNAL"] = "⬇️ PUT BUY"

    def style_table(row):
        s = ['']*len(row)

        try:
            if row["STRIKE"] == be_strike:
                if signal_type == "CALL":
                    s = ['background-color:#00e676;color:black;font-weight:bold']*len(row)
                elif signal_type == "PUT":
                    s = ['background-color:#ff5252;color:white;font-weight:bold']*len(row)
        except:
            pass

        return s

    st.subheader("📊 OPTION CHAIN")
    st.table(ui.style.apply(style_table, axis=1))

else:
    st.info("Loading...")
