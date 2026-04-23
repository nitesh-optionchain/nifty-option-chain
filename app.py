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
DATA_FILE = "admin_data_v2.json" # Version change for dynamic structure
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

# ================= 4. SIDEBAR & REFRESH =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

# DYNAMIC DATA STRUCTURE: Har index ka apna data
all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}
})

# Current selected index ka data nikalna
if index_choice not in all_index_data:
    all_index_data[index_choice] = {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"}, "sr": {"support": "-", "resistance": "-"}}

current_idx_data = all_index_data[index_choice]

# ================= 5. SDK & STABLE DATA FETCH =================
# ===== SAFE NUBRA INIT =====
if "nubra" not in st.session_state:
    try:
        st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except Exception as e:
        st.error("❌ Nubra SDK init failed")
        st.write(e)
        st.stop()

# ===== CREATE OBJECT =====
market_data = MarketData(st.session_state.nubra)

# ===== SAFE API CALL =====
try:
    result = market_data.option_chain(index_choice, exchange=target_exch)
except Exception as e:
    st.error("❌ Nubra API Error")
    st.warning("Server down / rate limit / invalid response")
    st.write(e)
    st.stop()

# ===== VALIDATION =====
if not result or not result.chain:
    st.warning("⚠️ Data nahi aa raha (Empty response)")
    st.stop()

# ===== PROCESS =====
chain = result.chain

try:
    raw_spot = getattr(chain.ce[0], 'underlying_price', 
               getattr(chain, 'underlying_price', 
               getattr(chain, 'at_the_money_strike', 0)))

    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot

except Exception as e:
    st.warning("⚠️ Spot calculation error")
    st.write(e)
    spot = 0

st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ✅ BREAK EVEN (missing tha)
be_strike = int(df.loc[
    (df["open_interest_CE"] + df["open_interest_PE"]).idxmax(),
    "STRIKE"
])

# --- OI CHANGE ---
state_key = f"initial_df_{index_choice}"
if state_key not in st.session_state:
    st.session_state[state_key] = df.copy()

def calc_stable_oi(row, side):
    curr_oi = row[f"open_interest_{side}"]
    prev_oi = row.get(f"previous_close_oi_{side}", 0)
    if prev_oi == 0:
        init_df = st.session_state[state_key].set_index("STRIKE")
        strike = row["STRIKE"]
        if strike in init_df.index:
            prev_oi = init_df.loc[strike, f"open_interest_{side}"]
    return curr_oi - prev_oi

df["oi_chg_CE"] = df.apply(lambda r: calc_stable_oi(r, "CE"), axis=1)
df["oi_chg_PE"] = df.apply(lambda r: calc_stable_oi(r, "PE"), axis=1)

max_oi_ce = df["open_interest_CE"].max()
max_oi_pe = df["open_interest_PE"].max()
max_vol_ce = df["volume_CE"].max()
max_vol_pe = df["volume_PE"].max()
max_chg_ce = df["oi_chg_CE"].abs().max() or 1
max_chg_pe = df["oi_chg_PE"].abs().max() or 1

# ===== UI TABLE =====
def fmt_val(val, delta, m_val):
    pct = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

def fmt_chg(delta, m_delta):
    pct = (delta/m_delta*100) if m_delta > 0 else 0
    return f"{delta:+,}\n{pct:.1f}%"

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

# ===== STYLE FUNCTION =====
def style_table(row):
    s = [''] * len(row)
    s[3] = 'background-color:#f0f2f6;color:black;font-weight:bold'

    try:
        c_oi_p = float(row.iloc[0].split('\n')[-1].replace('%',''))
        c_ch_p = float(row.iloc[1].split('\n')[-1].replace('%',''))
        c_vo_p = float(row.iloc[2].split('\n')[-1].replace('%',''))
        p_vo_p = float(row.iloc[4].split('\n')[-1].replace('%',''))
        p_ch_p = float(row.iloc[5].split('\n')[-1].replace('%',''))
        p_oi_p = float(row.iloc[6].split('\n')[-1].replace('%',''))

        if c_oi_p >= 70: s[0] = 'background-color:#1976d2;color:white'
        if c_ch_p >= 70: s[1] = 'background-color:#4caf50;color:white'
        if c_vo_p >= 70: s[2] = 'background-color:#1b5e20;color:white'
        if p_vo_p >= 70: s[4] = 'background-color:#b71c1c;color:white'
        if p_ch_p >= 70: s[5] = 'background-color:#f44336;color:white'
        if p_oi_p >= 70: s[6] = 'background-color:#fb8c00;color:white'

        # ✅ clean BE line
        if row.iloc[3] == be_strike:
            for i in range(len(s)):
                s[i] += 'border-top:3px solid #00e676; border-bottom:3px solid #00e676;'

        if row.iloc[3] == atm_strike:
            s[3] = 'background-color:yellow;color:black;font-weight:bold'

    except:
        pass

    return s

# ===== FINAL RENDER =====
st.subheader(f"📊 {index_choice} Option Chain")
st.table(ui.style.apply(style_table, axis=1))
