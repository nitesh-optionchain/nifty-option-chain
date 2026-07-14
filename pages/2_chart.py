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

# 🔐 SECURE OS INJECTION ENGINE (Fixes No Auth Token Found)
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# 🔄 SAFE ENGINE INITIALIZATION BIND (Bypasses Event Loop Closed Crashes)
@st.cache_resource(show_spinner=False)
def get_cached_market_engine():
    try:
        # Strictly PROD credentials initialize
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as e:
        print(f"SDK Engine Error: {str(e)}")
        return None

market_engine = get_cached_market_engine()

# Master Storage Structure Mapping Template
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# 🌐 HTML JavaScript Frame Injector WITH DYNAMIC LIVE DATA PUSHER LOOP
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Fallback to empty if authorization has totally broken down
    st.session_state.master_storage["NIFTY"]["master_history"] = []
    st.session_state.master_storage["SENSEX"]["master_history"] = []

    if market_engine:
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=5)
            
            # 1. Fetch HISTORICAL Data for NIFTY
            nifty_res = market_engine.historical_data({
                "exchange": "NSE",
                "type": "STOCK",
                "values": ["NIFTY"],
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

            # 2. Fetch HISTORICAL Data for SENSEX
            sensex_res = market_engine.historical_data({
                "exchange": "BSE",
                "type": "STOCK",
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
            st.warning(f"⚠️ Connection Warning: Data pipeline sync is waiting for connection updates.")
    else:
        st.error("🔒 Auth Fail: Credentials not processed. Please reboot the app in dashboard control.")

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
