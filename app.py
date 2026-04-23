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
                else:
                    st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})

if index_choice not in all_index_data:
    all_index_data[index_choice] = {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}

current_idx_data = all_index_data[index_choice]

# ================= 5. SDK =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain

    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price',
                   getattr(chain, 'underlying_price',
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except:
        spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # ================= OI CHANGE =================
    df["oi_chg_CE"] = df["open_interest_CE"].diff().fillna(0)
    df["oi_chg_PE"] = df["open_interest_PE"].diff().fillna(0)

    max_oi_ce = df["open_interest_CE"].max()
    max_oi_pe = df["open_interest_PE"].max()
    max_vol_ce = df["volume_CE"].max()
    max_vol_pe = df["volume_PE"].max()

    # ================= BREAK EVEN =================
    ce_resistance = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
    pe_support = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

    # ================= TABLE =================
    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    atm_idx = df.index[df["STRIKE"] == atm_strike][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    def fmt_val(val, delta, m):
        p = (val/m*100) if m > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    # ================= SIGNAL =================
    def get_signal(strike):
        if strike == pe_support:
            return "🟢⬆ CALL BUY"
        elif strike == ce_resistance:
            return "🔴⬇ PUT BUY"
        return ""

    ui["SIGNAL"] = d_df["STRIKE"].apply(get_signal)

    # ================= STYLE =================
    def style_table(row):
        styles = [''] * len(row)

        if row["STRIKE"] == pe_support:
            styles = ['background-color:#00e676;color:black;font-weight:bold'] * len(row)

        elif row["STRIKE"] == ce_resistance:
            styles = ['background-color:#ff1744;color:white;font-weight:bold'] * len(row)

        return styles

    st.subheader(f"📊 {index_choice} Option Chain (Break-Even Enabled)")
    st.table(ui.style.apply(style_table, axis=1))

else:
    st.info("Market data load ho raha hai...")
