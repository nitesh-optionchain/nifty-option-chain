import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode page configuration (Aapka original layout)
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 📂 Paths Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Secure Environment Keys Bridge
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Master Data Storage Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# 🔄 Pure Original SDK Initialization Logic
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    st.error(f"❌ SDK Connection Failure: {str(e)}")

# ⚡ CORE DATA INTEGRATION ENGINE
if market_engine:
    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=5)
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        # 1. NIFTY Data Fetch
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
            st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
            
            try:
                nifty_res = market_engine.historical_data({
                    "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if nifty_res and hasattr(nifty_res, 'result') and nifty_res.result and len(nifty_res.result) > 0:
                    res_obj = nifty_res.result[0]
                    if hasattr(res_obj, 'values') and res_obj.values and len(res_obj.values) > 0:
                        data_map = res_obj.values[0]
                        if isinstance(data_map, dict) and "NIFTY" in data_map:
                            raw_n = data_map["NIFTY"]
                            if hasattr(raw_n, 'open') and raw_n.open:
                                st.session_state.master_storage["NIFTY"]["master_history"] = [
                                    {"open": float(raw_n.open[i].value)/100, "high": float(raw_n.high[i].value)/100, 
                                     "low": float(raw_n.low[i].value)/100, "close": float(raw_n.close[i].value)/100}
                                    for i in range(len(raw_n.open))
                                ]
            except Exception:
                pass

        # 2. SENSEX Data Fetch
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
            st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
            
            try:
                sensex_res = market_engine.historical_data({
                    "exchange": "BSE", "type": "INDEX", "values": ["SENSEX"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if sensex_res and hasattr(sensex_res, 'result') and sensex_res.result and len(sensex_res.result) > 0:
                    res_obj_s = sensex_res.result[0]
                    if hasattr(res_obj_s, 'values') and res_obj_s.values and len(res_obj_s.values) > 0:
                        data_map_s = res_obj_s.values[0]
                        if isinstance(data_map_s, dict) and "SENSEX" in data_map_s:
                            raw_s = data_map_s["SENSEX"]
                            if hasattr(raw_s, 'open') and raw_s.open:
                                st.session_state.master_storage["SENSEX"]["master_history"] = [
                                    {"open": float(raw_s.open[i].value)/100, "high": float(raw_s.high[i].value)/100, 
                                     "low": float(raw_s.low[i].value)/100, "close": float(raw_s.close[i].value)/100}
                                    for i in range(len(raw_s.open))
                                ]
            except Exception:
                pass
            
    except Exception as error:
        st.warning(f"⚠️ Live data stream update delayed: {error}")

# 🔘 MANUAL REFRESH BUTTON
col1, col2 = st.columns([1, 8])
with col1:
    if st.button("🔄 Refresh Data"):
        st.rerun()

# 🌐 HTML JavaScript Frame Injector
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
