from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.admin_name = "Guest"

# ================= 2. FILE STORAGE (DATA PERSISTENCE) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "admin_data.json")
USER_FILE = os.path.join(BASE_DIR, "authorized_users.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: pass
    return {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
        "sr": {"support": "-", "resistance": "-"}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

def load_users():
    default_admins = {"9304768496": "Admin Chief"}
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f: return json.load(f)
        except: pass
    return default_admins

data = load_data()
ADMIN_DB = load_users()

# ================= 3. LOGIN FIREWALL =================
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("Login"):
            u_key = st.text_input("Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if u_key in ADMIN_DB:
                    st.session_state.auth = True
                    st.session_state.admin_name = ADMIN_DB[u_key]
                    st.rerun()
                else: st.error("Invalid ID")
    st.stop()

# ================= 4. DASHBOARD REFRESH =================
st_autorefresh(interval=5000, key="refresh") # 5 seconds auto-update

# ================= 5. DATA FETCH & CALCULATION =================
try:
    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

    market_data = MarketData(st.session_state.nubra)
    result = market_data.option_chain("NIFTY", exchange="NSE")

    if result:
        chain = result.chain
        spot = (chain.ce[0].underlying_price / 100) if chain.ce else chain.at_the_money_strike / 100
        
        st.title(f"🛡️ LIVE NIFTY: {spot:,.2f}")

        # DataFrames processing
        df_ce = pd.DataFrame([vars(x) for x in chain.ce])
        df_pe = pd.DataFrame([vars(x) for x in chain.pe])
        df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
        df["STRIKE"] = (df["strike_price"]/100).astype(int)

        # OI & Price Change Logic
        if "prev_df" not in st.session_state: st.session_state.prev_df = None
        if st.session_state.prev_df is not None:
            p = st.session_state.prev_df.set_index("STRIKE")
            c = df.set_index("STRIKE")
            df["oi_chg_CE"] = df["STRIKE"].map(c["open_interest_CE"] - p["open_interest_CE"]).fillna(0)
            df["oi_chg_PE"] = df["STRIKE"].map(c["open_interest_PE"] - p["open_interest_PE"]).fillna(0)
            df["prc_chg_CE"] = df["STRIKE"].map(c["last_traded_price_CE"] - p["last_traded_price_CE"]).fillna(0)
            df["prc_chg_PE"] = df["STRIKE"].map(c["last_traded_price_PE"] - p["last_traded_price_PE"]).fillna(0)
        else:
            df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0
        st.session_state.prev_df = df.copy()

        # ================= 6. MANUAL ENTRY (SIGNALS & S/R) =================
        st.markdown("---")
        col_sig, col_sr = st.columns([2, 1])
        
        with col_sig:
            st.subheader("🎯 SIGNAL PANEL")
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            m_stk = sc1.text_input("Strike", value=data["signal"]["Strike"])
            m_ent = sc2.text_input("Entry", value=data["signal"]["Entry"])
            m_tgt = sc3.text_input("Target", value=data["signal"]["Target"])
            m_sl  = sc4.text_input("SL", value=data["signal"]["SL"])
            if sc5.button("UPDATE SIGNAL"):
                data["signal"] = {"Strike": m_stk, "Entry": m_ent, "Target": m_tgt, "SL": m_sl, "Status": "LIVE"}
                save_data(data)
                st.rerun()

        with col_sr:
            st.subheader("📊 S/R PANEL")
            sr1, sr2, sr3 = st.columns(3)
            m_sup = sr1.text_input("Sup", value=data["sr"]["support"])
            m_res = sr2.text_input("Res", value=data["sr"]["resistance"])
            if sr3.button("SET LEVELS"):
                data["sr"] = {"support": m_sup, "resistance": m_res}
                save_data(data)
                st.rerun()

        # Display Metrics
        st.markdown("### ⚡ Live Metrics")
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("🟢 SUPPORT", data["sr"]["support"])
        m_c2.metric("🔴 RESISTANCE", data["sr"]["resistance"])
        m_c3.metric("🎯 ENTRY STRIKE", data["signal"]["Strike"])
        m_c4.metric("📊 SIGNAL STATUS", data["signal"]["Status"])

        # ================= 7. TABLE STYLING (ORIGINAL) =================
        def format_ui(val, delta, m_val):
            pct = (val/m_val*100) if m_val > 0 else 0
            return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

        def get_buildup(p, o):
            if p > 0 and o > 0: return "🟢 LONG"
            if p < 0 and o > 0: return "🔴 SHORT"
            return "⚪ -"

        atm = int(spot)
        # Finding the closest strike for ATM highlighting
        atm_idx = df.index[df["STRIKE"] >= atm][0]
        display_df = df.iloc[max(atm_idx-8,0): atm_idx+9].copy()

        ui = pd.DataFrame()
        ui["CE BUILDUP"] = display_df.apply(lambda r: get_buildup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
        ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
        ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
        ui["STRIKE"] = display_df["STRIKE"]
        ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_ui(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
        ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_ui(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)
        ui["PE BUILDUP"] = display_df.apply(lambda r: get_buildup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

        def apply_original_style(row):
            styles = [''] * len(row)
            try:
                ce_oi_pct = float(row.iloc[1].split('\n')[-1].replace('%',''))
                pe_oi_pct = float(row.iloc[5].split('\n')[-1].replace('%',''))
                # Original CE OI Deep Blue
                if ce_oi_pct > 65: styles[1] = 'background-color:#0d47a1;color:white;font-weight:bold'
                # Original PE OI Orange
                if pe_oi_pct > 65: styles[5] = 'background-color:#e65100;color:white;font-weight:bold'
                # Original ATM Yellow
                if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold;border:1px solid black'
                else: styles[3] = 'background-color:#f5f5f5'
            except: pass
            return styles

        st.subheader("📊 Institutional Option Chain")
        st.table(ui.style.apply(apply_original_style, axis=1))

    else:
        st.warning("🔄 Fetching Data from SDK...")

except Exception as e:
    st.error(f"Error: {e}")
