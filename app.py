from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# ================= CONFIG =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# Custom CSS for Big Live Price
st.markdown("""
    <style>
    .big-font {
        font-size:50px !important;
        font-weight: bold;
        color: #00ff00;
    }
    .price-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00ff00;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= FILE STORAGE =================
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

# ================= ADMIN =================
ADMIN_DB = {"9304768496": "Admin Chief", "9822334455": "Amit Kumar"}
url_id = st.query_params.get("id", None)
is_admin = url_id in ADMIN_DB

# ================= SDK =================
if "nubra" not in st.session_state:
    st.session_state.nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

nubra = st.session_state.nubra
market_data = MarketData(nubra)

# ================= DATA FETCH =================
result = market_data.option_chain("NIFTY", exchange="NSE")
if not result:
    st.warning("Waiting for Market Data...")
    st.stop()

chain = result.chain

# ================= LIVE NIFTY CALCULATION =================
try:
    spot = chain.ce[0].underlying_price / 100
    atm_val = int(round(spot / 50) * 50)
    prev_close = 24500 # Ise actual close se replace karein
    change_pts = spot - prev_close
    change_pct = (change_pts / prev_close) * 100
    color = "lawngreen" if change_pts >= 0 else "red"
except:
    spot, atm_val, change_pts, change_pct, color = 0.0, 0, 0.0, 0.0, "white"

# ================= HERO SECTION (LIVE NIFTY ALAG SE) =================
st.title("🛡️ SMART WEALTH AI 5")

# Live Nifty ka alag bada block
st.markdown(f"""
    <div class="price-card">
        <p style="margin:0; font-size:20px; color:white;">📊 NIFTY 50 LIVE PRICE</p>
        <span class="big-font" style="color:{color};">{spot:,.2f}</span>
        <span style="font-size:25px; color:{color}; margin-left:15px;">
            {change_pts:+.2f} ({change_pct:+.2f}%)
        </span>
    </div>
    """, unsafe_allow_html=True)

# Baaki secondary metrics
m1, m2, m3 = st.columns(3)
m1.metric("🎯 CURRENT ATM", f"{atm_val}")
m2.metric("📉 INDIA VIX", "13.45", "-1.1%")
m3.metric("⚖️ STATUS", "BULLISH 🚀" if change_pts > 0 else "BEARISH 📉")

st.markdown("---")

# ================= TRADINGVIEW CHART =================
tradingview_widget = """
<div class="tradingview-widget-container">
  <div id="tv-chart-nifty-v2"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({
    "width": "100%", "height": 500, "symbol": "NSE:NIFTY",
    "interval": "5", "timezone": "Asia/Kolkata", "theme": "dark",
    "style": "1", "locale": "en", "container_id": "tv-chart-nifty-v2"
  });
  </script>
</div>
"""
components.html(tradingview_widget, height=520)

# ================= DATAFRAME & OPTION CHAIN (SAME AS BEFORE) =================
df_ce = pd.DataFrame([vars(x) for x in chain.ce])
df_pe = pd.DataFrame([vars(x) for x in chain.pe])
df = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
df["STRIKE"] = (df["strike_price"]/100).astype(int)

if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

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

# ================= ADMIN SIGNALS (SAME) =================
st.subheader("🎯 LIVE TRADE SIGNALS")
c1, c2, c3, c4, c5 = st.columns(5)
if is_admin:
    s_strike = c1.text_input("Strike", value=data["signal"]["Strike"])
    s_entry = c2.text_input("Entry", value=data["signal"]["Entry"])
    s_target = c3.text_input("Target", value=data["signal"]["Target"])
    s_sl = c4.text_input("SL", value=data["signal"]["SL"])
    if c5.button("📢 UPDATE"):
        data["signal"] = {"Strike": s_strike, "Entry": s_entry, "Target": s_target, "SL": s_sl, "Status": "LIVE"}
        save_data(data)
        st.rerun()
else:
    c1.info(f"STRIKE: {data['signal']['Strike']}")
    c2.success(f"ENTRY: {data['signal']['Entry']}")
    c3.warning(f"TARGET: {data['signal']['Target']}")
    c4.error(f"SL: {data['signal']['SL']}")
    c5.write(f"**STATUS:** {data['signal']['Status']}")

# ================= OPTION CHAIN UI (SAME) =================
def format_val(val, delta, m_val):
    p = (val/m_val*100) if m_val > 0 else 0
    return f"{val:,.0f}\n({delta:+,})\n{p:.1f}%"

atm_int = int(spot)
atm_idx = df.index[df["STRIKE"] >= atm_int][0]
display_df = df.iloc[max(atm_idx-7,0): atm_idx+8].copy()

ui = pd.DataFrame()
ui["CE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_CE"], r["oi_chg_CE"], df["open_interest_CE"].max()), axis=1)
ui["CE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_CE"], 0, df["volume_CE"].max()), axis=1)
ui["STRIKE"] = display_df["STRIKE"]
ui["PE VOL\n(%)"] = display_df.apply(lambda r: format_val(r["volume_PE"], 0, df["volume_PE"].max()), axis=1)
ui["PE OI\n(Δ/%)"] = display_df.apply(lambda r: format_val(r["open_interest_PE"], r["oi_chg_PE"], df["open_interest_PE"].max()), axis=1)

def final_style(row):
    styles = [''] * len(row)
    try:
        c_oi = float(row.iloc[0].split('\n')[-1].replace('%',''))
        p_oi = float(row.iloc[4].split('\n')[-1].replace('%',''))
        if c_oi > 65: styles[0] = 'background-color:#0d47a1;color:white'
        if p_oi > 65: styles[4] = 'background-color:#ff6f00;color:white'
        if row.iloc[2] == atm_int: styles[2] = 'background-color:yellow;color:black;font-weight:bold'
    except: pass
    return styles

st.table(ui.style.apply(final_style, axis=1))
