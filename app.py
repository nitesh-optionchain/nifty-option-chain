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

# ================= 2. FILE STORAGE =================
DATA_FILE = "admin_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {
        "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
        "sr": {"support": "-", "resistance": "-"}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ================= 3. ADMIN AUTHORIZATION (FIREWALL) =================
ADMIN_DB = {
    "9304768496": "Admin Chief", 
    "9822334455": "Amit Kumar",
    "9011223344": "Amit Sharma"
}

# URL check (Agar link me ID ho)
query_params = st.query_params
url_id = query_params.get("id", None)
if url_id in ADMIN_DB:
    st.session_state.is_auth = True
    st.session_state.admin_name = ADMIN_DB[url_id]

# Login Screen (Agar authorized nahi hai)
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center; color: #00ff00;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Security Verification Required</h3>", unsafe_allow_html=True)
    
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Authorized Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.rerun()
                else:
                    st.error("❌ Unauthorized Access Denied")
    st.stop() # Yahan ruk jayega jab tak login na ho

# ================= 4. DASHBOARD STARTS (Authorized Only) =================
st_autorefresh(interval=5000, key="refresh")
st.sidebar.success(f"⚡ {st.session_state.admin_name}")
if st.sidebar.button("Logout"):
    st.session_state.is_auth = False
    st.rerun()

# ================= 5. SDK & DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(st.session_state.nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")

if not result:
    st.warning("🔄 Waiting for Live Market Data...")
    st.stop()

chain = result.chain

# Spot Price logic
try:
    # Latest attribute check logic
    raw_spot = getattr(chain.ce[0], 'underlying_price', 
               getattr(chain, 'underlying_price', 
               getattr(chain, 'at_the_money_strike', 0)))
    spot = raw_spot / 100 if raw_spot > 50000 else raw_spot
except:
    spot = 0

st.title("🛡️ SMART WEALTH AI 5")
st.subheader(f"📊 LIVE NIFTY: {spot:,.2f}")

# ================= 6. DATAFRAME & CALCULATIONS =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

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

# ================= 7. SIGNALS & S/R =================
st.subheader("🎯 LIVE TRADE SIGNALS")
c1, c2, c3, c4, c5 = st.columns(5)
s_strike = c1.text_input("Strike", value=data["signal"]["Strike"])
s_entry = c2.text_input("Entry", value=data["signal"]["Entry"])
s_target = c3.text_input("Target", value=data["signal"]["Target"])
s_sl = c4.text_input("SL", value=data["signal"]["SL"])

if c5.button("📢 UPDATE"):
    data["signal"] = {
        "Strike": s_strike, "Entry": s_entry, "Target": s_target,
        "SL": s_sl, "Status": f"LIVE ({st.session_state.admin_name})"
    }
    save_data(data)
    st.rerun()

st.subheader("📊 SUPPORT / RESISTANCE")
s1, s2, s3 = st.columns(3)
sup = s1.text_input("Support", data["sr"]["support"])
res = s2.text_input("Resistance", data["sr"]["resistance"])
if s3.button("SET"):
    data["sr"] = {"support": sup, "resistance": res}
    save_data(data)
    st.rerun()

a, b = st.columns(2)
a.metric("🟢 SUPPORT", data["sr"]["support"])
b.metric("🔴 RESISTANCE", data["sr"]["resistance"])

# ================= 8. TABLE UI & COLOR =================
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_CE"], r["oi_chg_CE"]), axis=1)
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)
ui["PE BUILDUP"] = display_df.apply(lambda r: get_bup(r["prc_chg_PE"], r["oi_chg_PE"]), axis=1)

def final_style(row):
    styles = [''] * len(row)
    try:
        ce_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
        pe_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))
        if ce_oi > 65: styles[1] = 'background-color:#0d47a1;color:white'
        if pe_oi > 65: styles[5] = 'background-color:#ff6f00;color:white'
        if row.iloc[3] == atm: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
        else: styles[3] = 'background-color:#eeeeee'
    except: pass
    return styles

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(final_style, axis=1))
