import streamlit as st
import pandas as pd
import requests
import json
import os
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & REFRESH =================
st.set_page_config(page_title="SMART WEALTH AI", layout="wide")
# Har 2 second mein page auto-refresh hoga taaki data live dikhe
st_autorefresh(interval=2000, key="live_refresh_9304")

SIG_FILE = "admin_levels_v2.json"

# ================= 2. DIRECT AUTO-FETCH LOGIC =================
def get_live_market_data(index_name):
    """Bina SDK ke direct API se data fetch karne ka function"""
    # NIFTY, BANKNIFTY, SENSEX ke liye dynamic URL
    url = f"https://api.nubra.in/v1/market/index/{index_name}"
    headers = {
        "api-key": "9304768496", # Aapki Mobile ID as API Key
        "Content-Type": "application/json"
    }
    
    try:
        # 5 second ka timeout taaki app hang na ho
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # LP = Last Price, CH = Change
            return {
                "lp": data.get("lp", 0.0), 
                "chg": data.get("ch", 0.0),
                "status": "LIVE ✅"
            }
        else:
            return {"lp": "ERR", "chg": 0.0, "status": f"Error {response.status_code}"}
    except Exception as e:
        return {"lp": "OFFLINE", "chg": 0.0, "status": "Connection Fail"}

# ================= 3. ADMIN DATA MANAGEMENT =================
def load_signals():
    if os.path.exists(SIG_FILE):
        with open(SIG_FILE, "r") as f:
            return json.load(f)
    return {"stk": "NIFTY 22500 CE", "buy": "150", "tgt": "200", "sl": "120"}

# ================= 4. MAIN DASHBOARD UI =================
st.title("📊 SMART WEALTH AI - LIVE TERMINAL")

# Sidebar for Market Selection
selected_index = st.sidebar.selectbox("Market Index", ["NIFTY", "BANKNIFTY", "SENSEX"])

# Fetching Data (Auto-Refresh handles the loop)
live_data = get_live_market_data(selected_index)
signals = load_signals()

# UI: Top Metric Card
m_color = "#00FF00" if str(live_data['lp']).replace('.','').isdigit() and live_data['chg'] >= 0 else "#FF4B4B"

st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:30px; border-radius:15px; border-left:10px solid {m_color}; text-align:center;">
        <h2 style="color:white; margin:0; font-family:sans-serif;">{selected_index}</h2>
        <h1 style="color:{m_color}; margin:10px 0; font-size:60px;">₹{live_data['lp']}</h1>
        <p style="color:{m_color}; margin:0; font-size:24px; font-weight:bold;">{live_data['chg']}% | {live_data['status']}</p>
    </div>
""", unsafe_allow_html=True)

# UI: Admin Update Panel
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🛠️ ADMIN SIGNAL CONTROL"):
    c1, c2, c3, c4 = st.columns(4)
    u_stk = c1.text_input("Strike", signals['stk'])
    u_buy = c2.text_input("Entry", signals['buy'])
    u_tgt = c3.text_input("Target", signals['tgt'])
    u_sl = c4.text_input("SL", signals['sl'])
    
    if st.button("PUSH SIGNAL TO LIVE", use_container_width=True):
        with open(SIG_FILE, "w") as f:
            json.dump({"stk": u_stk, "buy": u_buy, "tgt": u_tgt, "sl": u_sl}, f)
        st.success("Dashboard Updated!")
        st.rerun()

# UI: Trade Signal Metrics
st.markdown("---")
st.subheader("🎯 Active Trade Signal")
met1, met2, met3, met4 = st.columns(4)
met1.metric("INSTRUMENT", signals['stk'])
met2.metric("ENTRY PRICE", f"₹{signals['buy']}")
met3.metric("TARGET", f"₹{signals['tgt']}")
met4.metric("STOPLOSS", f"₹{signals['sl']}")

# UI: Live Option Chain (Placeholder)
st.markdown("---")
st.subheader("⚡ Live Option Chain Matrix")
try:
    # Option chain ke liye bhi direct fetch logic yahan aa sakta hai
    dummy_chain = pd.DataFrame({
        "CALL OI": [1200, 1500, 1800],
        "STRIKE": [int(float(live_data['lp']))-50, int(float(live_data['lp'])), int(float(live_data['lp']))+50],
        "PUT OI": [900, 1100, 1400]
    })
    st.table(dummy_chain)
except:
    st.info("Calculating strikes based on live price...")
