import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode configuration
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

# ==============================================================================
# 🔐 CRITICAL FIX: DIRECT CREDENTIAL INJECTION
# ==============================================================================
# Bhai, yahan cloud settings ke bajaye seedhe strings me apna real credentials daal do.
# Example: PHONE_NO = "9876543210" aur MPIN = "1234"
# Isse secrets bypass ho jayega aur SDK ko direct access mil jayega.
PHONE_NO = "YOUR_REAL_PHONE_NUMBER"  
MPIN = "YOUR_REAL_MPIN"              

os.environ["PHONE_NO"] = str(PHONE_NO)
os.environ["MPIN"] = str(MPIN)

# 🔄 System SDK Login Trigger
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    st.error(f"❌ SDK Connection Failure: {str(e)}")

# Master Storage Structure Mapping Template
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

if not market_engine:
    st.error("🔒 Auth Fail: Direct Broker connection verify nahi ho pa raha hai.")
    st.stop()

# 🌐 PURE HISTORICAL PRODUCTION DATA PARSING PIPELINE
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    st.session_state.master_storage["NIFTY"]["master_history"] = []
    st.session_state.master_storage["SENSEX"]["master_history"] = []

    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=5)
        
        # 1. Fetch REAL Data for NIFTY from PROD API
        nifty_res = market_engine.historical_data({
            "exchange": "NSE",
            "type": "INDEX",
            "values": ["Nifty 50"],
            "fields": ["open", "high", "low", "close", "cumulative_volume"],
            "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "10m",
            "intraDay": True,
            "realTime": False
        })
        
        if nifty_res and hasattr(nifty_res, 'candles') and nifty_res.candles:
            for candle in nifty_res.candles:
                raw_close = float(getattr(candle, 'close', 0)) / 100
                st.session_state.master_storage["NIFTY"]["price"] = int(getattr(candle, 'close', 0))
                st.session_state.master_storage["NIFTY"]["master_history"].append({
                    "time": getattr(candle, 'timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "open": float(getattr(candle, 'open', 0)) / 100,
                    "high": float(getattr(candle, 'high', 0)) / 100,
                    "low": float(getattr(candle, 'low', 0)) / 100,
                    "close": raw_close,
                    "volume": float(getattr(candle, 'cumulative_volume', 0))
                })

        # 2. Fetch REAL Data for SENSEX from PROD API
        sensex_res = market_engine.historical_data({
            "exchange": "BSE",
            "type": "INDEX",
            "values": ["SENSEX"],
            "fields": ["open", "high", "low", "close", "cumulative_volume"],
            "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "10m",
            "intraDay": True,
            "realTime": False
        })
        
        if sensex_res and hasattr(sensex_res, 'candles') and sensex_res.candles:
            for candle in sensex_res.candles:
                raw_close = float(getattr(candle, 'close', 0)) / 100
                st.session_state.master_storage["SENSEX"]["price"] = int(getattr(candle, 'close', 0))
                st.session_state.master_storage["SENSEX"]["master_history"].append({
                    "time": getattr(candle, 'timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "open": float(getattr(candle, 'open', 0)) / 100,
                    "high": float(getattr(candle, 'high', 0)) / 100,
                    "low": float(getattr(candle, 'low', 0)) / 100,
                    "close": raw_close,
                    "volume": float(getattr(candle, 'cumulative_volume', 0))
                })

    except Exception as data_err:
        st.error(f"❌ Operational API Exception: {str(data_err)}")

    # JSON dynamic generation
    json_data = json.dumps(st.session_state.master_storage)

    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
        
        window.addEventListener("message", function(event) {{
            if (event.data && event.data.type === "LIVE_TICK_UPDATE") {{
                window.chartData = event.data.payload;
                if(typeof fetchUpdates === "function") {{
                    fetchUpdates();
                }}
            }}
        }});
    </script>
    """
    
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
