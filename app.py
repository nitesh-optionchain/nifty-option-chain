from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import json, os

# ================= 1. CONFIG & AUTH STATE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"
    st.session_state.is_super_admin = False
    st.session_state.current_user_id = "" # Added to track current login

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
            json.dump(data_to_save, f, indent=4)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 3. LOGIN FIREWALL (SESSION PERSISTENCE FIX) =================
# Pehle check karo ki kya koi purani session file padi hai
if "is_auth" not in st.session_state:
    if os.path.exists("session_login.json"):
        try:
            with open("session_login.json", "r") as f:
                saved = json.load(f)
                st.session_state.is_auth = True
                st.session_state.admin_name = saved["admin_name"]
                st.session_state.current_user_id = saved["user_id"]
                st.session_state.is_super_admin = saved["is_super_admin"]
        except:
            st.session_state.is_auth = False
    else:
        st.session_state.is_auth = False

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
                    st.session_state.current_user_id = user_key
                    st.session_state.is_super_admin = True if user_key in SUPER_ADMIN_IDS else False
                    
                    # Login hote hi file save karo (taki logout na ho)
                    session_data = {
                        "user_id": user_key,
                        "admin_name": st.session_state.admin_name,
                        "is_super_admin": st.session_state.is_super_admin
                    }
                    with open("session_login.json", "w") as f:
                        json.dump(session_data, f)
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

# Purana logout hata kar ye lagayein
if st.sidebar.button("🔒 LOGOUT"):
    if os.path.exists("session_login.json"):
        os.remove("session_login.json") # Ye line session clear kar degi
    st.session_state.is_auth = False
    st.rerun()

all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "BANKNIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})

if index_choice not in all_index_data:
    all_index_data[index_choice] = {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}

current_idx_data = all_index_data[index_choice]

# ================= 5. SENSEX LIVE HEADER (TRADING VIEW) =================
if index_choice == "SENSEX":
    tv_html = """
    <div class="tradingview-widget-container">
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
      {"symbol": "BSE:SENSEX", "width": "100%", "colorTheme": "light", "isTransparent": false, "locale": "en"}
      </script>
    </div>
    """
    components.html(tv_html, height=130)

# ================= 6. SDK & STABLE DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain(index_choice, exchange=target_exch)

if result and result.chain:
    chain = result.chain
    try:
        raw_spot = getattr(chain.ce[0], 'underlying_price', 
                   getattr(chain, 'underlying_price', 
                   getattr(chain, 'at_the_money_strike', 0)))
        spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
    except: spot = 0

    st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df["STRIKE"] = (df["strike_price"]/100).astype(int)

    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state:
        st.session_state[state_key] = df.copy()

    def calc_stable_oi(row, side):
        curr_oi = row[f"open_interest_{side}"]
        init_df = st.session_state[state_key].set_index("STRIKE")
        strike = row["STRIKE"]
        prev_oi = init_df.loc[strike, f"open_interest_{side}"] if strike in init_df.index else curr_oi
        return curr_oi - prev_oi

    df["oi_chg_CE"] = df.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
    df["oi_chg_PE"] = df.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

    max_oi_ce, max_oi_pe = df["open_interest_CE"].max(), df["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df["volume_CE"].max(), df["volume_PE"].max()
    max_chg_ce = df["oi_chg_CE"].abs().max() if df["oi_chg_CE"].abs().max() > 0 else 1
    max_chg_pe = df["oi_chg_PE"].abs().max() if df["oi_chg_PE"].abs().max() > 0 else 1

    be_res_strike = int(df.loc[df["open_interest_CE"].idxmax(), "STRIKE"])
    be_sup_strike = int(df.loc[df["open_interest_PE"].idxmax(), "STRIKE"])

    # Auto Signal Alert
    if spot >= be_res_strike:
        st.success(f"🚀 BIG MOVE: {index_choice} CALL BUYING ABOVE {be_res_strike}")
    elif spot <= be_sup_strike:
        st.error(f"🩸 BIG MOVE: {index_choice} PE BUYING BELOW {be_sup_strike}")

    # ================= 7. ADMIN PANEL & METRICS =================
    if st.session_state.is_super_admin:
        with st.expander(f"🛠️ ADMIN CONTROLS ({index_choice})"):
            t1, t2 = st.tabs(["Signal & Levels", "User Management"])
            with t1:
                c1, c2, c3, c4 = st.columns(4)
                s_stk = c1.text_input("Strike", value=current_idx_data["signal"]["Strike"])
                s_ent = c2.text_input("Entry Price", value=current_idx_data["signal"]["Entry"])
                s_tgt = c3.text_input("Target", value=current_idx_data["signal"]["Target"])
                s_sl = c4.text_input("SL", value=current_idx_data["signal"]["SL"])
                sup_in = st.text_input("Support", value=current_idx_data["sr"]["support"])
                res_in = st.text_input("Resistance", value=current_idx_data["sr"]["resistance"])
                
                if st.button(f"UPDATE {index_choice} DATA"):
                    all_index_data[index_choice]["signal"] = {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl}
                    all_index_data[index_choice]["sr"] = {"support": sup_in, "resistance": res_in}
                    save_json(DATA_FILE, all_index_data)
                    st.success("Levels Updated!")
                    st.rerun()
            with t2:
                st.markdown("#### ➕ Add New User")
                new_uid = st.text_input("New Mobile ID")
                new_uname = st.text_input("User Name")
                if st.button("ADD NEW USER"):
                    if new_uid and new_uname:
                        ADMIN_DB[new_uid] = new_uname
                        save_json(USER_FILE, ADMIN_DB)
                        st.success("User Added!")
                        st.rerun()
                    else: st.warning("Please fill all details.")
                
                st.divider()
                
                st.markdown("#### 🗑️ Delete User")
                # Exclude the current logged-in super admin from deletion list for safety
                delete_list = {f"{v} ({k})": k for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id}
                
                if delete_list:
                    selected_user_to_del = st.selectbox("Select User to Remove", list(delete_list.keys()))
                    if st.button("REMOVE SELECTED USER", type="primary"):
                        uid_to_remove = delete_list[selected_user_to_del]
                        del ADMIN_DB[uid_to_remove]
                        save_json(USER_FILE, ADMIN_DB)
                        st.error(f"User {selected_user_to_del} removed!")
                        st.rerun()
                else:
                    st.info("No other users to delete.")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🎯 STRIKE", current_idx_data["signal"]["Strike"])
    m2.metric("💰 ENTRY", current_idx_data["signal"]["Entry"])
    m3.metric("📈 TARGET", current_idx_data["signal"]["Target"])
    m4.metric("📉 SL", current_idx_data["signal"]["SL"])
    m5.metric("🟢 SUP", current_idx_data["sr"]["support"])
    m6.metric("🔴 RES", current_idx_data["sr"]["resistance"])

   # ================= 8. TABLE UI & COLOUR LOGIC =================
    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    def fmt_chg(delta, m_delta):
        pct = (delta/m_delta*100) if m_delta > 0 else 0
        return f"{delta:+,}\n{pct:.1f}%"

    # Find ATM
    atm_strike = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
    atm_idx = df.index[df["STRIKE"] == atm_strike][0]
    
    # Slice and RESET INDEX (Bahut Zaroori Hai)
    d_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy().reset_index(drop=True)

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
        try:
            # Current row data from d_df using index
            idx = row.name
            cur_strike = int(d_df.loc[idx, "STRIKE"])
            
            # Extract percentages for highlighting
            # row.iloc[0] = CE OI, row.iloc[1] = CE OI CHG, row.iloc[2] = CE VOL
            c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
            c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
            c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
            
            p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
            p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
            p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

            # Highest Volume values in current view
            max_vol_ce_view = d_df["volume_CE"].max()
            max_vol_pe_view = d_df["volume_PE"].max()
            raw_vol_ce = d_df.loc[idx, "volume_CE"]
            raw_vol_pe = d_df.loc[idx, "volume_PE"]

            # --- 1. STRIKE & ATM Highlight ---
            s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold' 
            if cur_strike == int(atm_strike):
                s[3] = 'background-color:yellow;color:black;font-weight:bold'

            # --- 2. OI & OI CHG Logic ---
            if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
            if c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
            if p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
            if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'

            # --- 3. Volume & Trap Filter ---
            # CE Volume: Highest or > 75%
            if raw_vol_ce == max_vol_ce_view or c_vo_p >= 75:
                s[2] = 'background-color:#1b5e20;color:white'

            # PE Volume: Highest or > 75%
            if raw_vol_pe == max_vol_pe_view or p_vo_p >= 75:
                s[4] = 'background-color:#b71c1c;color:white'

            # --- 4. Support/Resistance Borders (Overwrites if needed) ---
            if cur_strike == be_res_strike:
                for i in range(len(s)): s[i] += '; border-top: 3px solid blue; border-bottom: 3px solid blue'
            if cur_strike == be_sup_strike:
                for i in range(len(s)): s[i] += '; border-top: 3px solid red; border-bottom: 3px solid red'

        except Exception as e:
            pass
        return s

    st.subheader(f"📊 {index_choice} Option Chain")
    st.table(ui.style.apply(style_table, axis=1))
else:
    st.info("Market data load ho raha hai...")
