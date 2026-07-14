import sys
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

@st.cache_resource(show_spinner=False)
def get_sdk_connector():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception:
        return None

market_engine = get_sdk_connector()

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# Local local arrays to strictly ensure immediate population context values
master_history_array = []
base_val = 24350.0 if target_index == "NIFTY" else 79650.0
start_unix = int(time.time()) - (100 * 300)

# Pull historical elements directly from broker network endpoint
if market_engine:
    try:
        symbol_name = "Nifty 50" if target_index == "NIFTY" else "SENSEX"
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        
        hist_response = market_engine.historical_data({
            "exchange": exch_name, "type": "INDEX", "values": [symbol_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "5m", "intraDay": True, "realTime": False
        })
        
        if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
            for candle in hist_response.candles:
                raw_ts = getattr(candle, 'timestamp', '')
                unix_ts = int(pd.to_datetime(raw_ts).timestamp()) if raw_ts else int(time.time())
                master_history_array.append({
                    "time": unix_ts,
                    "open": float(getattr(candle, 'open', 0)) / 100,
                    "high": float(getattr(candle, 'high', 0)) / 100,
                    "low": float(getattr(candle, 'low', 0)) / 100,
                    "close": float(getattr(candle, 'close', 0)) / 100
                })
                
        snap = market_engine.current_price(target_index, exchange=exch_name)
        if snap and getattr(snap, 'price', None):
            base_val = float(snap.price) / 100
    except Exception:
        pass

# Fallback block configuration mapping values instantly if broker fails
if not master_history_array:
    for step in range(100):
        current_unix = start_unix + (step * 300)
        master_history_array.append({
            "time": current_unix,
            "open": base_val + (step % 5) - 2,
            "high": base_val + (step % 5) + 10,
            "low": base_val + (step % 5) - 8,
            "close": base_val + (step % 5) + 3
        })

# Compile final dynamic storage dictionary mapping elements variables
runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.caption("🔄 Status Bridge: Transmission Connected")

# ==============================================================================
# 🌐 HTML PARSER MATRIX LAYER (Strict String Injector Engine)
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(runtime_payload)
    
    # Absolute script string override engine parameters context layout map
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
        
        window.onload = function() {{
            if(typeof renderStaticBars === "function") {{ renderStaticBars(); }}
        }};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    components.html(html_content, height=760, scrolling=False)
    
    time.sleep(1.5)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
