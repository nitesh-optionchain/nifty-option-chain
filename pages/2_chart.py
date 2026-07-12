import sys
from types import ModuleType
import os
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode page configuration
st.set_page_config(layout="wide")

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

# --- 🎯 TIME FRAME & ASSET STATE SELECTORS ---
if "user_asset" not in st.session_state:
    st.session_state.user_asset = "NIFTY"
if "user_tf" not in st.session_state:
    st.session_state.user_tf = "5m"

col_ui1, col_ui2 = st.columns([2, 2])
with col_ui1:
    st.session_state.user_asset = st.selectbox("🎯 Asset Index", ["NIFTY", "SENSEX"], index=0 if st.session_state.user_asset == "NIFTY" else 1)
with col_ui2:
    tf_list = ["5m", "10m", "15m", "30m", "1d", "1w"]
    st.session_state.user_tf = st.selectbox("⏳ Timeframe", tf_list, index=tf_list.index(st.session_state.user_tf))

# Master Data Storage Framework
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "HISTORICAL", "master_history": []},
        "SENSEX": {"price": 0, "status": "HISTORICAL", "master_history": []}
    }

# 🔄 Pure Original SDK Initialization Logic
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    st.error(f"❌ SDK Connection Failure: {str(e)}")

# ⚡ DYNAMIC HISTORICAL DATA FETCH ENGINE
if market_engine:
    try:
        active_asset = st.session_state.user_asset
        active_tf = st.session_state.user_tf
        
        # Calculate timeframe history depth
        end_dt = datetime.utcnow()
        days_back = 30 if ("d" in active_tf or "w" in active_tf) else 5
        start_dt = end_dt - timedelta(days=days_back)
        
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")
        
        exch = "BSE" if active_asset == "SENSEX" else "NSE"
        
        # Fetching bulk historical candles pack
        response = market_engine.historical_data({
            "exchange": exch,
            "type": "INDEX",
            "values": [active_asset],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_str,
            "endDate": end_str,
            "interval": active_tf,
            "intraDay": True if "m" in active_tf else False,
            "realTime": False
        })
        
        if response and hasattr(response, 'result') and response.result:
            raw_candles = response.result[0].values[0][active_asset]
            parsed_history = []
            for i in range(len(raw_candles.open)):
                parsed_history.append({
                    "open": float(raw_candles.open[i].value) / 100,
                    "high": float(raw_candles.high[i].value) / 100,
                    "low": float(raw_candles.low[i].value) / 100,
                    "close": float(raw_candles.close[i].value) / 100
                })
            st.session_state.master_storage[active_asset]["master_history"] = parsed_history
            st.session_state.master_storage[active_asset]["status"] = "LOADED"
            
            # Live snap injection for latest tracking metrics
            snap = market_engine.current_price(active_asset, exchange=exch)
            if snap and snap.price:
                st.session_state.master_storage[active_asset]["price"] = int(snap.price)
                
    except Exception as error:
        st.warning(f"⚠️ Data extraction delayed: {error}")

# 🌐 HTML JavaScript Frame Injector
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{st.session_state.user_asset}";
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")
