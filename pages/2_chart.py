import sys
from types import ModuleType
import os
import time
import json
from datetime import datetime
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
from nubra_python_sdk.ticker import websocketdata  # ✅ Strict Live Ticker Import

# 🔐 SECURE OS INJECTION ENGINE
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Initialize master storage in session state exactly as your template expects
if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 24150.00, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 77300.00, "status": "LIVE", "master_history": []}
    }

# ==============================================================================
# 🔌 3. NUBRA REAL WEBSOCKET RUNNING ENGINE CORE (Your exact working VS Code script)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def initialize_live_ohlcv_stream():
    try:
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        # ✅ Your exact raw data parser that logs into VS Code terminal successfully
        def on_ohlcv_data(msg):
            try:
                sym = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                if sym in ["NIFTY", "SENSEX"]:
                    # Unpacking native integer paise units safely into decimal float rupees
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    v = float(getattr(msg, 'bucket_volume', 0))
                    
                    if c > 0:
                        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        storage = st.session_state.master_storage[sym]
                        storage["price"] = c
                        storage["status"] = "LIVE"
                        
                        # Strict timestamp variable formatting required by lightweight candles
                        buf = storage["master_history"]
                        if len(buf) > 0 and buf[-1]["time"] == time_str:
                            buf[-1].update({"high": max(buf[-1]["high"], h), "low": min(buf[-1]["low"], l), "close": c, "volume": buf[-1]["volume"] + v})
                        else:
                            buf.append({"time": time_str, "open": o, "high": h, "low": l, "close": c, "volume": v})
                            
                        if len(buf) > 300:
                            buf.pop(0)
            except Exception as loop_e:
                print(f"Callback structure exception: {loop_e}")

        socket = websocketdata.NubraDataSocket(
            client=nubra,
            on_ohlcv_data=on_ohlcv_data,
            on_connect=lambda m: print("[status]", m),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}")
        )
        
        socket.connect()
        socket.subscribe(["NIFTY"], data_type="ohlcv", interval="10m", exchange="NSE")
        socket.subscribe(["SENSEX"], data_type="ohlcv", interval="10m", exchange="BSE")
        return socket
    except Exception as initialization_err:
        print(f"Socket infrastructure initialization failure: {initialization_err}")
        return None

# Instantiating the streaming broker proxy
stream_broker = initialize_live_ohlcv_stream()

# ==============================================================================
# 🌐 4. HTML JAVASCRIPT CANVAS FRAME INJECTOR
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Fallback placeholder seeder to ensure timeline never stands completely white on initial launch
    for key in ["NIFTY", "SENSEX"]:
        cell = st.session_state.master_storage[key]
        if len(cell["master_history"]) == 0:
            base_v = cell["price"]
            cell["master_history"] = [
                {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "open": base_v, "high": base_v, "low": base_v, "close": base_v, "volume": 0.0}
            ]

    # JSON dynamic generation from state dict memory
    json_data = json.dumps(st.session_state.master_storage)

    # Injected JavaScript script block targeting your postMessage hooks explicitly
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
        
        // Dynamic messaging bridge loop matching your custom frame trigger
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
    
    # Render standalone native canvas frame
    components.html(html_content, height=850, scrolling=True)
    
    # ⏳ Hidden Background dynamic auto-trigger state (refresh bypass)
    st.empty()
    time.sleep(1)
    st.rerun() 
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
