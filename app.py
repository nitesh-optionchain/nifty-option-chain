from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = "Guest"

# ================= 2. FILES =================
DATA_FILE = "admin_data_v2.json"
USER_FILE = "authorized_users.json"

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f)
    except:
        pass

# ================= 3. ADMINS (3 USERS) =================
ADMIN_DB = load_json(USER_FILE, {
    "9304768496": "Admin Chief",
    "7982046438": "Admin X",
    "9999999999": "Admin Y"
})

# ================= 4. LOGIN =================
if not st.session_state.is_auth:
    st.title("🛡️ SMART WEALTH AI 5")

    user_key = st.text_input("Enter Admin ID", type="password")

    if st.button("LOGIN"):
        if user_key in ADMIN_DB:
            st.session_state.is_auth = True
            st.session_state.admin_name = ADMIN_DB[user_key]
            st.session_state.is_super_admin = True
            st.rerun()
        else:
            st.error("Invalid ID")
    st.stop()

# ================= 5. SIDEBAR =================
st_autorefresh(interval=5000, key="refresh")

st.sidebar.markdown(f"### 👤 {st.session_state.admin_name}")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])
target_exch = "NSE" if index_choice == "NIFTY" else "BSE"

if st.sidebar.button("LOGOUT"):
    st.session_state.is_auth = False
    st.rerun()

# ================= 6. SHARED DATA =================
all_index_data = load_json(DATA_FILE, {
    "NIFTY": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"},
              "sr": {"support": "-", "resistance": "-"}},
    "SENSEX": {"signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"},
               "sr": {"support": "-", "resistance": "-"}}
})

if index_choice not in all_index_data:
    all_index_data[index_choice] = {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-"},
        "sr": {"support": "-", "resistance": "-"}
    }

current = all_index_data[index_choice]

# ================= 7. NUBRA INIT =================
if "nubra" not in st.session_state:
    try:
        st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except Exception as e:
        st.error("SDK Error")
        st.stop()

market_data = MarketData(st.session_state.nubra)

try:
    result = market_data.option_chain(index_choice, exchange=target_exch)
except Exception as e:
    st.error("API ERROR")
    st.stop()

if not result or not result.chain:
    st.warning("No Data")
    st.stop()

chain = result.chain

try:
    raw_spot = getattr(chain.ce[0], "underlying_price",
                       getattr(chain, "underlying_price",
                       getattr(chain, "at_the_money_strike", 0)))

    spot = raw_spot / 100 if raw_spot > 100000 else raw_spot
except:
    spot = 0

st.title(f"SMART WEALTH AI 5 | {index_choice}: {spot:,.2f}")

# ================= 8. DATAFRAME =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])

df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE", "_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"] / 100).astype(int)

# ================= BREAK EVEN =================
be_strike = int(df.loc[
    (df["open_interest_CE"] + df["open_interest_PE"]).idxmax(),
    "STRIKE"
])

# ================= OI CHANGE =================
state_key = f"init_{index_choice}"
if state_key not in st.session_state:
    st.session_state[state_key] = df.copy()

def oi_change(row, side):
    curr = row[f"open_interest_{side}"]
    init = st.session_state[state_key].set_index("STRIKE")
    strike = row["STRIKE"]
    if strike in init.index:
        return curr - init.loc[strike, f"open_interest_{side}"]
    return 0

df["oi_chg_CE"] = df.apply(lambda r: oi_change(r, "CE"), axis=1)
df["oi_chg_PE"] = df.apply(lambda r: oi_change(r, "PE"), axis=1)

# ================= ADMIN PANEL =================
if st.session_state.is_super_admin:
    with st.expander("🛠️ ADMIN PANEL (LIVE)"):
        c1, c2, c3, c4 = st.columns(4)

        s_stk = c1.text_input("Strike", value=current["signal"]["Strike"])
        s_ent = c2.text_input("Entry", value=current["signal"]["Entry"])
        s_tgt = c3.text_input("Target", value=current["signal"]["Target"])
        s_sl  = c4.text_input("SL", value=current["signal"]["SL"])

        sup = st.text_input("Support", value=current["sr"]["support"])
        res = st.text_input("Resistance", value=current["sr"]["resistance"])

        if st.button("SAVE DATA"):
            all_index_data[index_choice]["signal"] = {
                "Strike": s_stk,
                "Entry": s_ent,
                "Target": s_tgt,
                "SL": s_sl
            }

            all_index_data[index_choice]["sr"] = {
                "support": sup,
                "resistance": res
            }

            save_json(DATA_FILE, all_index_data)
            st.success("UPDATED FOR ALL USERS")
            st.rerun()

# ================= METRICS =================
m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("STRIKE", current["signal"]["Strike"])
m2.metric("ENTRY", current["signal"]["Entry"])
m3.metric("TARGET", current["signal"]["Target"])
m4.metric("SL", current["signal"]["SL"])
m5.metric("SUPPORT", current["sr"]["support"])
m6.metric("RESISTANCE", current["sr"]["resistance"])

# ================= TABLE =================
atm = df.loc[(df["STRIKE"] - spot).abs().idxmin(), "STRIKE"]
idx = df.index[df["STRIKE"] == atm][0]
d = df.iloc[max(idx-7,0): idx+8]

ui = pd.DataFrame()
ui["CE OI"] = d["open_interest_CE"]
ui["STRIKE"] = d["STRIKE"]
ui["PE OI"] = d["open_interest_PE"]

# ================= STYLE =================
def style(row):
    s = [''] * len(row)

    if row["STRIKE"] == be_strike:
        s = ['border-top:3px solid green'] * len(row)

    if row["STRIKE"] == atm:
        s[1] = "background:yellow;color:black"

    return s

st.subheader("OPTION CHAIN")
st.table(ui.style.apply(style, axis=1))
