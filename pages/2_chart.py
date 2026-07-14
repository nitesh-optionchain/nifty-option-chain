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

# 🔐 SECURE OS INJECTION ENGINE
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# 🔄 System SDK Login Trigger (Cached to prevent multi-thread connection breaks)
@st.cache_resource(show_spinner=False)
def initialize_sdk_market_engine():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception as e:
        print(f"SDK Engine Error: {str(e)}")
        return None

market_engine = initialize_sdk_market_engine()

# Initialize Master Storage in Session State
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

# ✅ FIX 1: Safe Guard Layer instead of harsh st.stop() which blanks out Cloud containers
if not market_engine:
    st.error("🔒 Auth Fail: Broker connection setup complete nahi ho pa raha hai. Please check credentials or repository settings.")
else:
    # 🌐 HISTORICAL BASED DATA PARSING PIPELINE
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Resetting arrays before active database refresh checks
        st.session_state.master_storage["NIFTY"]["master_history"] = []
        st.session_state.master_storage["SENSEX"]["master_history"] = []

        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=5)
            
            # 🔄 FIX 2: Replaced realtime tickers with solid Historical Data API mappings
            # 1. Fetch NIFTY Historical Rows
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

            # 2. Fetch SENSEX Historical Rows
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
                
            # Maintain array sizes efficiently
            if len(st.session_state.master_storage["NIFTY"]["master_history"]) > 300:
                st.session_state.master_storage["NIFTY"]["master_history"] = st.session_state.master_storage["NIFTY"]["master_history"][-300:]
            if len(st.session_state.master_storage["SENSEX"]["master_history"]) > 300:
                st.session_state.master_storage["SENSEX"]["master_history"] = st.session_state.master_storage["SENSEX"]["master_history"][-300:]
                
        except Exception as data_err:
            st.warning(f"⚠️ Pipeline Notice: Historical extraction sync delay ({str(data_err)})")

        # JSON generation matching original messaging system
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
        
        # Render clean static view frame
        components.html(html_content, height=850, scrolling=True)
        
        # 🔄 FIX 3: Removed explicit background st.rerun() loop which causes memory exhaustion on Linux clouds.
        # Streamlit updates now flow smoothly on page event context updates.
    else:
        st.error("❌ 'index.html' file root folder me nahi mili!")
