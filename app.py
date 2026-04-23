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
    st.session_state.admin_name = "Guest"
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
                else: st.error("❌ Invalid ID")
    st.stop()

# ================= 4. SIDEBAR & SWITCH LOGIC =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

# YAHAN CHANGE HAI: Symbol aur Exchange dono switch honge
index_choice = st.sidebar.selectbox("Select Market", ["NIFTY", "SENSEX"])

if index_choice == "SENSEX":
    target_symbol = "SENSEX"
    target_exch = "BSE"
else:
    target_symbol = "NIFTY"
    target_exch = "NSE"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

current_data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 5. DATA FETCHING =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
# target_symbol aur target_exch ab dynamic hain
result = market_data.option_chain(target_symbol, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 
                   getattr(chain, 'underlying_price', 
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ {target_symbol} ({target_exch}) | Spot: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # --- STABLE OI LOGIC ---
    state_key = f"base_{target_symbol}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()
    
    base_df = st.session_state[state_key].set_index("STRIKE")
    curr_indexed = df.set_index("STRIKE")
    
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: curr_indexed.loc[x, "open_interest_CE"] - base_df.loc[x, "open_interest_CE"] if x in base_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: curr_indexed.loc[x, "open_interest_PE"] - base_df.loc[x, "open_interest_PE"] if x in base_df.index else 0)

    # Max values for colors
    m_oi_c, m_oi_p = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    m_vol_c, m_vol_p = df["volume_CE"].max(), df["volume_PE"].max()
    m_chg_c = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    m_chg_p = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    # ================= 6. ADMIN PANEL =================
    if st.session_state.is_super_admin:
        with st.expander("🎯 SET LEVELS"):
            c1, c2 = st.columns(2)
            sup = c1.text_input("Support", current_data["sr"]["support"])
            res = c2.text_input("Resistance", current_data["sr"]["resistance"])
            if st.button("SAVE LEVELS"):
                current_data["sr"] = {"support": sup, "resistance": res}
                save_json(DATA_FILE, current_data)
                st.rerun()

    st.write(f"🟢 **SUP:** {current_data['sr']['support']} | 🔴 **RES:** {current_data['sr']['resistance']}")

    # ================= 7. TABLE UI =================
    def fmt(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100 if m>0 else 0):.1f}%"
    def fmt_c(d, m): return f"{d:+,}\n{(d/m*100 if m>0 else 0):.1f}%"

    atm_idx = (df['STRIKE'] - spot).abs().idxmin()
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_CE"], r["oi_chg_CE"], m_oi_c), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_c(r["oi_chg_CE"], m_chg_c), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_c(r["oi_chg_PE"], m_chg_p), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt(r["open_interest_PE"], r["oi_chg_PE"], m_oi_p), axis=1)

    def styling(row):
        s = [''] * len(row)
        try:
            c_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            p_p = float(row.iloc[3].split('\n')[-1].replace('%',''))
            if c_p >= 70: s[1] = 'background-color:#4caf50;color:white'
            if p_p >= 70: s[3] = 'background-color:#f44336;color:white'
            if row.iloc[2] == int(spot/100)*100: s[2] = 'background-color:yellow'
        except: pass
        return s

    st.table(ui.style.apply(styling, axis=1))
else:
    st.error(f"Data not found for {index_choice}. Check if market is open.")
