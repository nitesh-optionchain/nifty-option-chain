import sys
from types import ModuleType
import os
import time
import json
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

# 🔄 System SDK Login Trigger
market_engine = None
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(client)
except Exception as e:
    print(f"SDK Engine Error: {str(e)}")

if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

if not market_engine:
    st.error("🔒 Auth Fail: Broker connection structure ready nahi ho paya.")
    st.stop()

# 🌐 HTML JavaScript Frame Injector WITH DYNAMIC LIVE DATA PUSHER LOOP
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Yahan hum market engine se direct dynamic ticks fetch karenge loop ke andar
    try:
        # 1. Fetch NIFTY
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            real_nifty = float(nifty_snap.price) / 100
            st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
            st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
            st.session_state.master_storage["NIFTY"]["master_history"].append({
                "open": real_nifty, "high": real_nifty, "low": real_nifty, "close": real_nifty
            })

        # 2. Fetch SENSEX
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            real_sensex = float(sensex_snap.price) / 100
            st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
            st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
            st.session_state.master_storage["SENSEX"]["master_history"].append({
                "open": real_sensex, "high": real_sensex, "low": real_sensex, "close": real_sensex
            })
            
        # Limits maintain array size
        if len(st.session_state.master_storage["NIFTY"]["master_history"]) > 300:
            st.session_state.master_storage["NIFTY"]["master_history"].pop(0)
        if len(st.session_state.master_storage["SENSEX"]["master_history"]) > 300:
            st.session_state.master_storage["SENSEX"]["master_history"].pop(0)
            
    except Exception as data_err:
        print(f"Tick collect alert: {data_err}")

    # JSON dynamic generation
    json_data = json.dumps(st.session_state.master_storage)

    # 🎯 YAHAN HAI ASLI POSTMESSAGE CONTROLLER:
    # Yeh script page load hote hi iframe ke andar ek continuous listener set karega
    # Aur ek hidden timer har 1 second me bina main page ko hilaaye sirf data refresh logic push karega.
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.streamAuthContext = {{"STATUS": "AUTHORIZED_SECURE_MODE"}};
        
        // Dynamic messaging bridge loop
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
    
    # Render static frame ONLY ONCE
    components.html(html_content, height=850, scrolling=True)
    
    # ⏳ Hidden Background dynamic auto-trigger state (refresh bypass)
    st.empty()
    time.sleep(1)
    st.rerun() # Yeh rerun background me chalega bina UI tearing ke kyunki framework inject ho chuka hai
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
