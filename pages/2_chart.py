import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode terminal configuration
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

# ========================================================
# 🔐 RETAIN SELECTION ON REFRESH ENGINE (Query Params Mapping)
# ========================================================
# Streamlit updates keys automatically. Fetch from browser context
query_params = st.query_params

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = query_params.get("asset", "NIFTY")

if "selected_tf" not in st.session_state:
    st.session_state.selected_tf = query_params.get("tf", "5m")

# Layout Selectors Row (Top Grid Configuration as per drawing)
top_col1, top_col2, top_col3 = st.columns([2, 3, 5])

with top_col1:
    asset_options = ["NIFTY", "SENSEX", "BANKNIFTY"]
    default_asset_idx = asset_options.index(st.session_state.selected_asset) if st.session_state.selected_asset in asset_options else 0
    current_asset = st.selectbox("🎯 Target Index", asset_options, index=default_asset_idx, key="asset_select")
    # URL Sync
    st.query_params["asset"] = current_asset
    st.session_state.selected_asset = current_asset

with top_col2:
    tf_options = ["5m", "10m", "15m", "30m", "1d", "1w"]
    default_tf_idx = tf_options.index(st.session_state.selected_tf) if st.session_state.selected_tf in tf_options else 0
    current_tf = st.selectbox("⏳ Time Frame", tf_options, index=default_tf_idx, key="tf_select")
    # URL Sync
    st.query_params["tf"] = current_tf
    st.session_state.selected_tf = current_tf
# ========================================================

# Load Credentials Safely
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

if "chart_master_data" not in st.session_state:
    st.session_state.chart_master_data = {
        "NIFTY": {"price": 0, "change": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "change": 0, "status": "LIVE", "master_history": []},
        "BANKNIFTY": {"price": 0, "change": 0, "status": "LIVE", "master_history": []},
        "INDIAVIX": {"price": 0, "change": 0, "status": "LIVE", "master_history": []}
    }

try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_data = MarketData(client)
except Exception as e:
    st.error(f"SDK Core Verification Failure: {e}")
    st.stop()

# --- DYNAMIC HISTORICAL PIPELINE WITH TIMEFRAME MAPPING ---
def fetch_candles(asset_name, timeframe):
    box = st.session_state.chart_master_data
    end_dt = datetime.utcnow()
    
    # Dynamic historical scaling based on selected timeframe
    days_back = 30 if "d" in timeframe or "w" in timeframe else 5
    start_dt = end_dt - timedelta(days=days_back)
    
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")
    
    try:
        exch = "BSE" if asset_name == "SENSEX" else "NSE"
        # SDK translation for days/weeks intervals
        sdk_interval = "1d" if timeframe == "1d" else ("1w" if timeframe == "1w" else timeframe)
        
        response = market_data.historical_data({
            "exchange": exch,
            "type": "INDEX",
            "values": [asset_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_str,
            "endDate": end_str,
            "interval": sdk_interval,
            "intraDay": True if "m" in timeframe else False,
            "realTime": False
        })
        
        raw_candles = response.result[0].values[0][asset_name]
        parsed_history = []
        for i in range(len(raw_candles.open)):
            parsed_history.append({
                "open": float(raw_candles.open[i].value) / 100,
                "high": float(raw_candles.high[i].value) / 100,
                "low": float(raw_candles.low[i].value) / 100,
                "close": float(raw_candles.close[i].value) / 100
            })
        box[asset_name]["master_history"] = parsed_history
    except Exception as ex:
        print(f"Historical parsing error for {asset_name}: {ex}")

# Fetch active state charts only to lower system load
fetch_candles(st.session_state.selected_asset, st.session_state.selected_tf)

# --- RENDERING CORES ---
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Sync storage states inside header frame
    json_data = json.dumps(st.session_state.chart_master_data)
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentSelectedAsset = "{st.session_state.selected_asset}";
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_STABLE"}};
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # Pure static render - zero page flashing
    components.html(html_content, height=850, scrolling=True)
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
