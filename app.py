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
        with open(file_path, "w") as f: json.dump(data_to_save, f)
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
current_idx_data = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= 5. SDK & STABLE DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', getattr(chain, 'underlying_price', 0))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce, df_pe = pd.DataFrame([vars(x) for x in chain.ce]), pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    # OI Change Logic
    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state: st.session_state[state_key] = df.copy()
    init_df = st.session_state[state_key].set_index("STRIKE")
    
    df["oi_chg_CE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_CE"] - init_df.loc[x, "open_interest_CE"] if x in init_df.index else 0)
    df["oi_chg_PE"] = df["STRIKE"].map(lambda x: df.set_index("STRIKE").loc[x, "open_interest_PE"] - init_df.loc[x, "open_interest_PE"] if x in init_df.index else 0)

    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce, max_chg_pe = df["oi_chg_CE"].abs().max() or 1, df["oi_chg_PE"].abs().max() or 1

    # BREAK-EVEN CALCULATION (Highest OI Points)
    be_res = df.loc[df["open_interest_CE"].idxmax(), "STRIKE"]
    be_sup = df.loc[df["open_interest_PE"].idxmax(), "STRIKE"]

    # ================= 6. AUTO SIGNAL ALERT =================
    if spot >= be_res:
        st.success(f"🔥 BIG MOVE ALERT: CALL BUYING ZONE ABOVE {be_res} (Resistance Broken!)")
    elif spot <= be_sup:
        st.error(f"🩸 BIG MOVE ALERT: PUT BUYING ZONE BELOW {be_sup} (Support Broken!)")

    # Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🎯 STRIKE", current_idx_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_idx_data["signal"]["Entry"])
    m3.metric("📈 TARGET", current_idx_data["signal"]["Target"])
    m4.metric("📉 SL", current_idx_data["signal"]["SL"])
    m5.metric("🟢 SUP", current_idx_data["sr"]["support"])
    m6.metric("🔴 RES", current_idx_data["sr"]["resistance"])

    # ================= 7. TABLE UI & STYLING =================
    def fmt_val(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100 if m>0 else 0):.1f}%"
    def fmt_chg(d, m): return f"{d:+,}\n{(d/m*100 if m>0 else 0):.1f}%"

    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    atm_idx = df.index[df["STRIKE"] == atm_strike][0]
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_CE"], max_chg_ce), axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"]
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: fmt_chg(r["oi_chg_PE"], max_chg_pe), axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s = [''] * len(row)
        strike = row.iloc[3]
        s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold' # Default Grey

        # --- BIG MOVE LINE LOGIC ---
        if strike == be_res: # Resistance Line
            s = ['border-top: 3px solid #0000FF; border-bottom: 3px solid #0000FF; font-weight:bold'] * len(row)
        if strike == be_sup: # Support Line
            s = ['border-top: 3px solid #FF0000; border-bottom: 3px solid #FF0000; font-weight:bold'] * len(row)
            
        # --- FULL ROW HIGHLIGHT ON BREAKOUT ---
        if spot > be_res and strike == be_res: # Buy Signal Row
            s = ['background-color: #90EE90; color: black; font-weight: bold; border: 2px solid green'] * len(row)
        elif spot < be_sup and strike == be_sup: # Sell Signal Row
            s = ['background-color: #FFB6C1; color: black; font-weight: bold; border: 2px solid red'] * len(row)

        try:
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))
            if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
            if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'
            if strike == atm_strike: s[3] = 'background-color:yellow;color:black'
        except: pass
        return s

    st.subheader(f"📊 {index_choice} Option Chain")
    st.table(ui.style.apply(style_table, axis=1))

    # Admin Panel (Same Tabs)
    if st.session_state.is_super_admin:
        with st.expander("🛠️ ADMIN CONTROLS"):
            t1, t2 = st.tabs(["Signals", "Users"])
            with t1:
                c1, c2, c3, c4 = st.columns(4)
                s_stk = c1.text_input("Strike", value=current_idx_data["signal"]["Strike"])
                s_ent = c2.text_input("Entry", value=current_idx_data["signal"]["Entry"])
                sup_in = st.text_input("Support", value=current_idx_data["sr"]["support"])
                res_in = st.text_input("Resistance", value=current_idx_data["sr"]["resistance"])
                if st.button(f"UPDATE {index_choice}"):
                    all_index_data[index_choice]["signal"].update({"Strike": s_stk, "Entry": s_ent})
                    all_index_data[index_choice]["sr"].update({"support": sup_in, "resistance": res_in})
                    save_json(DATA_FILE, all_index_data)
                    st.rerun()
            with t2:
                nu = st.text_input("Mobile ID")
                if st.button("ADD"):
                    ADMIN_DB[nu] = "New Admin"
                    save_json(USER_FILE, ADMIN_DB)
                    st.success("Added")
else:
    st.info("Market data load ho raha hai...")
