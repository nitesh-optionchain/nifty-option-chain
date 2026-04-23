from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import json, os

# ================= 1. CONFIG =================
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
            return json.load(open(file_path, "r"))
        except:
            return default_val
    return default_val

def save_json(file_path, data):
    try:
        json.dump(data, open(file_path, "w"))
    except:
        pass

ADMIN_DB = load_json(USER_FILE, {
    "9304768496": "Admin Chief",
    "7982046438": "Admin x"
})

SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# ================= 3. LOGIN =================
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align:center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)

    _, col2, _ = st.columns([1,1,1])
    with col2:
        with st.form("login"):
            uid = st.text_input("Enter Mobile ID", type="password")
            if st.form_submit_button("LOGIN"):
                if uid in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[uid]
                    st.session_state.is_super_admin = uid in SUPER_ADMIN_IDS
                    st.rerun()
                else:
                    st.error("❌ Invalid Access ID")

    st.stop()

# ================= 4. REFRESH =================
st_autorefresh(interval=5000, key="refresh")

st.sidebar.markdown(f"### 👤 User: **{st.session_state.admin_name}**")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

# 🔥 FIXED LOGOUT (SAFE RESET)
if st.sidebar.button("🔒 LOGOUT"):
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"
    st.session_state.is_super_admin = False

    if "nubra" in st.session_state:
        del st.session_state["nubra"]

    st.rerun()

# ================= DATA =================
all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike":"-","Entry":"-","Target":"-","SL":"-"},
              "sr": {"support":"-","resistance":"-"}},
    "SENSEX": {"signal": {"Strike":"-","Entry":"-","Target":"-","SL":"-"},
               "sr": {"support":"-","resistance":"-"}}
})

current = all_index_data.get(index_choice, all_index_data["NIFTY"])

# ================= SDK SAFE INIT =================
if "nubra" not in st.session_state:
    try:
        st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except Exception:
        st.error("❌ SDK INIT FAILED")
        st.stop()

market_data = MarketData(st.session_state.nubra)

# ================= API SAFE =================
try:
    result = market_data.option_chain(index_choice, exchange=target_exch)
except Exception:
    st.error("❌ API ERROR")
    st.stop()

if not result or not result.chain:
    st.warning("⚠️ No Data")
    st.stop()

chain = result.chain

# ================= SPOT =================
try:
    raw = getattr(chain.ce[0], 'underlying_price',
           getattr(chain, 'underlying_price',
           getattr(chain, 'at_the_money_strike', 0)))

    spot = raw / 100 if raw > 100000 else raw
except:
    spot = 0

st.title(f"🛡️ SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

# ================= DATAFRAME =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# ================= BREAK EVEN =================
be_strike = int(df.loc[df["open_interest_CE"].idxmax(), "STRIKE"])

# ================= OI =================
key = f"init_{index_choice}"
if key not in st.session_state:
    st.session_state[key] = df.copy()

def oi_change(row, side):
    curr = row[f"open_interest_{side}"]
    init = st.session_state[key].set_index("STRIKE")
    s = row["STRIKE"]
    prev = init.loc[s, f"open_interest_{side}"] if s in init.index else curr
    return curr - prev

df["oi_chg_CE"] = df.apply(lambda r: oi_change(r,"CE"), axis=1)
df["oi_chg_PE"] = df.apply(lambda r: oi_change(r,"PE"), axis=1)

# ================= ADMIN PANEL (UNCHANGED UI) =================
if st.session_state.is_super_admin:
    with st.expander(f"🛠️ ADMIN CONTROLS ({index_choice})"):
        c1,c2,c3,c4 = st.columns(4)

        s_stk = c1.text_input("Strike", current["signal"]["Strike"])
        s_ent = c2.text_input("Entry", current["signal"]["Entry"])
        s_tgt = c3.text_input("Target", current["signal"]["Target"])
        s_sl  = c4.text_input("SL", current["signal"]["SL"])

        sup = st.text_input("Support", current["sr"]["support"])
        res = st.text_input("Resistance", current["sr"]["resistance"])

        if st.button("UPDATE"):
            all_index_data[index_choice] = {
                "signal": {"Strike": s_stk, "Entry": s_ent, "Target": s_tgt, "SL": s_sl},
                "sr": {"support": sup, "resistance": res}
            }
            save_json(DATA_FILE, all_index_data)
            st.rerun()

# ================= METRICS =================
m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("🎯 STRIKE", current["signal"]["Strike"])
m2.metric("💰 ENTRY", current["signal"]["Entry"])
m3.metric("📈 TARGET", current["signal"]["Target"])
m4.metric("📉 SL", current["signal"]["SL"])
m5.metric("🟢 SUP", current["sr"]["support"])
m6.metric("🔴 RES", current["sr"]["resistance"])

# ================= TABLE (UNCHANGED COLOR LOGIC) =================
def style(row):
    s = [''] * len(row)

    if row.iloc[3] == be_strike:
        s = ['border:2px solid #00e676'] * len(row)

    try:
        if row.iloc[3] == int(df.loc[(df["STRIKE"]-spot).abs().idxmin(),"STRIKE"]):
            s[3] = 'background:yellow;font-weight:bold'
    except:
        pass

    return s

st.subheader("📊 Option Chain")
st.table(df.style.apply(style, axis=1))
