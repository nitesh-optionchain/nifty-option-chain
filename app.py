from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= 1. CONFIG & SESSION =================
st.set_page_config(page_title="SMART WEALTH AI 5 - SECURE", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ================= 2. FILE & DATA STORAGE =================
DATA_FILE = "admin_data.json"
USER_FILE = "authorized_users.json"

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except: pass
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# Master Admin setup
MASTER_ADMIN = "9304768496"
auth_users = load_json(USER_FILE, {MASTER_ADMIN: "Admin Chief"})
data = load_json(DATA_FILE, {
    "signal": {"Strike": "-", "Entry": "-", "Target": "-", "SL": "-", "Status": "WAITING"},
    "sr": {"support": "-", "resistance": "-"}
})

# ================= 3. LOGIN INTERFACE =================
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Security Login Required</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.form("Login"):
            mobile = st.text_input("Enter Registered Mobile Number", type="password")
            submit = st.form_submit_button("UNSEAL DASHBOARD")
            
            if submit:
                if mobile in auth_users:
                    st.session_state.authenticated = True
                    st.session_state.user_name = auth_users[mobile]
                    st.session_state.mobile = mobile
                    st.rerun()
                else:
                    st.error("🚫 Access Denied! Your number is not registered.")
    st.stop()

# ================= 4. DASHBOARD LOGIC (POST-LOGIN) =================
st_autorefresh(interval=5000, key="refresh")
is_admin = (st.session_state.mobile == MASTER_ADMIN)

# Sidebar
st.sidebar.title(f"👤 {st.session_state.user_name}")
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

if is_admin:
    with st.sidebar.expander("➕ ADD NEW USER"):
        u_name = st.text_input("User Name")
        u_mob = st.text_input("User Mobile")
        if st.button("Authorize User"):
            if u_name and u_mob:
                auth_users[u_mob] = u_name
                save_json(USER_FILE, auth_users)
                st.success(f"Registered: {u_name}")
            else: st.warning("Fill all details")
    
    st.sidebar.write("Registered Users:", list(auth_users.values()))

# ================= 5. SDK & DATA FETCH =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

nubra = st.session_state.nubra
market_data = MarketData(nubra)
result = market_data.option_chain("NIFTY", exchange="NSE")

if not result or not result.chain:
    st.info("🔄 Connecting to NSE Live Stream...")
    st.stop()

chain = result.chain

# Calculations
try:
    spot = float(chain.ce[0].underlying_price / 100)
    atm_val = int(round(spot / 50) * 50)
    prev_close = 24500 
    change_pts = spot - prev_close
    change_pct = (change_pts / prev_close) * 100
except:
    spot, atm_val, change_pts, change_pct = 0.0, 0, 0.0, 0.0

# ================= 6. HEADER & TICKER =================
ticker_html = """
<div class="tradingview-widget-container">
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-tickers.js" async>
  {"symbols": [{"proName": "NSE:NIFTY", "title": "NIFTY 50"},{"proName": "NSE:BANKNIFTY", "title": "BANK NIFTY"},{"proName": "BSE:SENSEX", "title": "SENSEX"},{"proName": "NSE:INDIAVIX", "title": "INDIA VIX"}],
  "colorTheme": "dark", "isTransparent": true, "locale": "en"}
  </script>
</div>
"""
components.html(ticker_html, height=80)

h1, h2, h3, h4 = st.columns(4)
h1.metric("📊 NIFTY LIVE", f"{spot:,.2f}", f"{change_pts:+.2f} ({change_pct:+.2f}%)")
h2.metric("🎯 CURRENT ATM", f"{atm_val}")
h3.metric("📉 INDIA VIX", "13.45", "-1.1%")
h4.metric("⚖️ STATUS", "BULLISH 🚀" if change_pts > 0 else "BEARISH 📉")

st.markdown("---")

# ================= 7. ADMIN SIGNALS =================
st.subheader("🎯 LIVE TRADE SIGNALS")
c1, c2, c3, c4, c5 = st.columns(5)

if is_admin:
    s_strike = c1.text_input("Strike", value=data["signal"]["Strike"])
    s_entry = c2.text_input("Entry", value=data["signal"]["Entry"])
    s_target = c3.text_input("Target", value=data["signal"]["Target"])
    s_sl = c4.text_input("SL", value=data["signal"]["SL"])
    if c5.button("📢 BROADCAST"):
        data["signal"] = {"Strike": s_strike, "Entry": s_entry, "Target": s_target, "SL": s_sl, "Status": "LIVE 🔥"}
        save_json(DATA_FILE, data)
        st.success("Signal Updated!")
else:
    c1.info(f"STRIKE: {data['signal']['Strike']}")
    c2.success(f"ENTRY: {data['signal']['Entry']}")
    c3.warning(f"TARGET: {data['signal']['Target']}")
    c4.error(f"SL: {data['signal']['SL']}")
    c5.write(f"**Status:** {data['signal']['Status']}")

# ================= 8. OPTION CHAIN (PRO LOGIC) =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

# Buildup tracking
if "prev_df" not in st.session_state: st.session_state.prev_df = None
if st.session_state.prev_df is not None:
    prev = st.session_state.prev_df.set_index("STRIKE")
    curr = df.set_index("STRIKE")
    df["oi_chg_CE"] = df["STRIKE"].map(curr["open_interest_CE"] - prev["open_interest_CE"]).fillna(0)
    df["oi_chg_PE"] = df["STRIKE"].map(curr["open_interest_PE"] - prev["open_interest_PE"]).fillna(0)
    df["prc_chg_CE"] = df["STRIKE"].map(curr["last_traded_price_CE"] - prev["last_traded_price_CE"]).fillna(0)
    df["prc_chg_PE"] = df["STRIKE"].map(curr["last_traded_price_PE"] - prev["last_traded_price_PE"]).fillna(0)
else:
    df["oi_chg_CE"] = df["oi_chg_PE"] = df["prc_chg_CE"] = df["prc_chg_PE"] = 0
st.session_state.prev_df = df.copy()

def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+.0f})\n{p:.1f}%"

def get_bup(p, o):
    if p > 0 and o > 0: return "🟢 LONG"
    if p < 0 and o > 0: return "🔴 SHORT"
    return "⚪ -"

atm_idx = df.index[df["STRIKE"] >= int(spot)][0]
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
        c_oi = float(row.iloc[1].split('\n')[-1].replace('%',''))
        p_oi = float(row.iloc[5].split('\n')[-1].replace('%',''))
        if c_oi > 65: styles[1] = 'background-color:#0d47a1;color:white'
        if p_oi > 65: styles[5] = 'background-color:#ff6f00;color:white'
        if row["STRIKE"] == atm_val: styles[3] = 'background-color:yellow;color:black;font-weight:bold'
        else: styles[3] = 'background-color:#eeeeee;color:black'
    except: pass
    return styles

st.subheader("📊 Institutional Option Chain")
st.table(ui.style.apply(final_style, axis=1))
