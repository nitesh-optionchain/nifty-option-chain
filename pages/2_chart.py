import sys
from types import ModuleType
import os
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode page configuration (Aapka original layout)
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

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

# 🔄 Pure Global Session Broker Engine Bridge
market_engine = None

# Agar pure application session me engine pehle hi kisi page par ban chuka hai, toh naya login mat karo
if "global_market_engine" in st.session_state and st.session_state.global_market_engine is not None:
    market_engine = st.session_state.global_market_engine
else:
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        market_engine = MarketData(client)
        # Is master engine connection ko humesha ke liye session me lock kar do
        st.session_state.global_market_engine = market_engine
    except Exception as e:
        st.error(f"❌ SDK Connection Failure: {str(e)}")

# ⚡ CORE DATA INTEGRATION ENGINE (Strict Documentation Realignment)
if market_engine:
    try:
        from datetime import datetime, timedelta
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=5)
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        def unpack_nubra_array(points_list):
            if not points_list:
                return []
            return [float(p.value) for p in points_list]

        # 1. NIFTY Data Fetch
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            st.session_state.master_storage["NIFTY"]["price"] = float(nifty_snap.price)
            st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
            
            try:
                nifty_res = market_engine.historical_data({
                    "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if nifty_res and hasattr(nifty_res, 'result') and nifty_res.result and len(nifty_res.result) > 0:
                    for instrument_dict in nifty_res.result[0].values:
                        if "NIFTY" in instrument_dict:
                            stock_chart = instrument_dict["NIFTY"]
                            opens = unpack_nubra_array(stock_chart.open)
                            highs = unpack_nubra_array(stock_chart.high)
                            lows = unpack_nubra_array(stock_chart.low)
                            closes = unpack_nubra_array(stock_chart.close)
                            
                            if len(opens) > 0:
                                st.session_state.master_storage["NIFTY"]["master_history"] = [
                                    {"open": opens[i]/100, "high": highs[i]/100, "low": lows[i]/100, "close": closes[i]/100}
                                    for i in range(len(opens))
                                ]
            except Exception as e:
                st.write(f"Nifty Hist Error: {e}")

        # 2. SENSEX Data Fetch
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            st.session_state.master_storage["SENSEX"]["price"] = float(sensex_snap.price)
            st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
            
            try:
                sensex_res = market_engine.historical_data({
                    "exchange": "BSE", "type": "INDEX", "values": ["SENSEX"],
                    "fields": ["open", "high", "low", "close"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, "realTime": False
                })
                if sensex_res and hasattr(sensex_res, 'result') and sensex_res.result and len(sensex_res.result) > 0:
                    for instrument_dict in sensex_res.result[0].values:
                        if "SENSEX" in instrument_dict:
                            stock_chart_s = instrument_dict["SENSEX"]
                            opens_s = unpack_nubra_array(stock_chart_s.open)
                            highs_s = unpack_nubra_array(stock_chart_s.high)
                            lows_s = unpack_nubra_array(stock_chart_s.low)
                            closes_s = unpack_nubra_array(stock_chart_s.close)
                            
                            if len(opens_s) > 0:
                                st.session_state.master_storage["SENSEX"]["master_history"] = [
                                    {"open": opens_s[i]/100, "high": highs_s[i]/100, "low": lows_s[i]/100, "close": closes_s[i]/100}
                                    for i in range(len(opens_s))
                                ]
            except Exception as e:
                st.write(f"Sensex Hist Error: {e}")
            
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
