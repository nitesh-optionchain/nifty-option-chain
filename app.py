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

# ================= 2. FILE STORAGE =================
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
st_autorefresh(interval=5000, key="refresh") 

# ================= 5. DATA FETCH & CALCULATION (FIXED) =================
try:
    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

    market_data = MarketData(st.session_state.nubra)
    result = market_data.option_chain("NIFTY", exchange="NSE")

    if result and result.chain:
        chain = result.chain
        
        # --- FIXED ATTRIBUTE FETCHING ---
        try:
            # underlying_price ki jagah alternate attributes check kar rahe hain
            raw_spot = getattr(chain.ce[0], 'underlying_price', 
                       getattr(chain, 'underlying_price', 
                       getattr(chain, 'at_the_money_strike', 0)))
            spot = raw_spot / 100 if raw_spot > 50000 else raw_spot # Handling multiplier
        except:
            spot = 0
        
        st.title(f"🛡️ LIVE NIFTY: {spot:,.2f}")

        # DataFrames
        df_ce = pd.DataFrame([vars(x) for x in chain.ce])
        df_pe = pd.DataFrame([vars(x) for x in chain.pe])
        df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
        df["STRIKE"] = (df["strike_price"]/100).astype(int)

        # Delta Calculation
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

        # ================= 6. UI ELEMENTS =================
        st.markdown("---")
        c_sig, c_sr = st.columns([2, 1])
        with c_sig:
            st.subheader("🎯 SIGNALS")
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            m_stk = sc1.text_input("Strike", value=data["signal"]["Strike"])
            m_ent = sc2.text_input("Entry", value=data["signal"]["Entry"])
            if sc5.button("UPDATE"):
                data["signal"].update({"Strike": m_stk, "Entry": m_ent, "Status": "LIVE"})
                save_data(data)
                st.rerun()

        with c_sr:
            st.subheader("📊 S/R")
            sr1, sr2, sr3 = st.columns(3)
            m_sup = sr1.text_input("Sup", value=data["sr"]["support"])
            if sr3.button("SET"):
                data["sr"]["support"] = m_sup
                save_data(data)
                st.rerun()

        # Metrics
        st.markdown("### ⚡ Metrics")
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("🟢 SUPPORT", data["sr"]["support"])
        m_c2.metric("🔴 RESISTANCE", data["sr"]["resistance"])
        m_c3.metric("🎯 ENTRY", data["signal"]["Strike"])
        m_c4.metric("📊 STATUS", data["signal"]["Status"])

        # ================= 7. TABLE (ORIGINAL STYLING) =================
        def format_ui(val, delta, m_val):
            pct = (val/m_val*100) if m_val > 0 else 0
            return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

        def get_buildup(p, o):
            return "🟢 LONG" if p > 0 and o > 0 else "🔴 SHORT" if p < 0 and o > 0 else "⚪ -"

        atm = int(spot)
        try:
            atm_idx = df.index[df["STRIKE"] >= atm][0]
            display_df = df.iloc[max(atm_idx-8,0): atm_idx+9].copy()
        except:
            display_df = df.head(15).copy()

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
                if ce_oi_pct > 65: styles[1] = 'background-color:#0d47a1;color:white;font-weight:bold'
                if pe_oi_pct > 65: styles[5] = 'background-color:#e65100;color:white;font-weight:bold'
                if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
                else: styles[3] = 'background-color:#f5f5f5'
            except: pass
            return styles

        st.subheader("📊 Institutional Option Chain")
        st.table(ui.style.apply(apply_original_style, axis=1))

    else:
        st.warning("🔄 Fetching Data...")

except Exception as e:
    st.error(f"Error encountered: {e}")
