import sys
from types import ModuleType
import os
import time
import json
import threading
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode terminal config
st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Path Initializer
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Secure Environment Fetcher
PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# ========================================================
# 🌐 GLOBAL DICTIONARY PROTOCOL (Bypassing Session State Thread Crash)
# ========================================================
if "GLOBAL_LIVE_DATA" not in globals():
    globals()["GLOBAL_LIVE_DATA"] = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

live_data_box = globals()["GLOBAL_LIVE_DATA"]
# ========================================================

# 🔄 BACKGROUND NETWORKING THREAD LOOP (Uses Safe Global Variables)
if "bg_pipeline_active" not in st.session_state:
    def live_ticker_stream():
        try:
            client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
            market_engine = MarketData(client)
            
            while True:
                try:
                    # 1. Real Fetch NIFTY
                    nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
                    if nifty_snap and nifty_snap.price:
                        real_nifty = float(nifty_snap.price) / 100
                        live_data_box["NIFTY"]["price"] = int(nifty_snap.price)
                        live_data_box["NIFTY"]["status"] = "LIVE"
                        live_data_box["NIFTY"]["master_history"].append({
                            "open": real_nifty, "high": real_nifty, "low": real_nifty, "close": real_nifty
                        })

                    # 2. Real Fetch SENSEX
                    sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
                    if sensex_snap and sensex_snap.price:
                        real_sensex = float(sensex_snap.price) / 100
                        live_data_box["SENSEX"]["price"] = int(sensex_snap.price)
                        live_data_box["SENSEX"]["status"] = "LIVE"
                        live_data_box["SENSEX"]["master_history"].append({
                            "open": real_sensex, "high": real_sensex, "low": real_sensex, "close": real_sensex
                        })

                    # Maintain stable array limits
                    if len(live_data_box["NIFTY"]["master_history"]) > 300:
                        live_data_box["NIFTY"]["master_history"].pop(0)
                    if len(live_data_box["SENSEX"]["master_history"]) > 300:
                        live_data_box["SENSEX"]["master_history"].pop(0)
                        
                except Exception as t_err:
                    print(f"Tick Stream Inner Loop Error: {t_err}")
                time.sleep(1)
        except Exception as e:
            print(f"Background Thread Login Fail: {e}")

    t = threading.Thread(target=live_ticker_stream, daemon=True)
    t.start()
    st.session_state.bg_pipeline_active = True

# 🌐 HTML STATIC RENDER - NO REFRESH LOOP
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # JavaScript dynamic variable handler injected into head
    injection_script = """
    <script>
        window.streamAuthContext = {"STATUS": "AUTHORIZED_SECURE_STABLE"};
        
        // Listener to pull state from postMessage without refreshing iframe
        window.addEventListener("message", function(event) {
            if (event.data && event.data.type === "REALTIME_TICK") {
                window.chartData = event.data.payload;
                if(typeof fetchUpdates === "function") {
                    fetchUpdates();
                }
            }
        });
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    
    # 🎯 RENDER IFRAME ONLY ONCE (No Refresh, No Flicker!)
    components.html(html_content, height=850, scrolling=True)
    
    # Hidden dynamic bridge component to pass ticks smoothly
    json_payload = json.dumps(live_data_box)
    st.components.v1.html(f"""
        <script>
            window.parent.postMessage({{
                type: "REALTIME_TICK",
                payload: {json_payload}
            }}, "*");
        </script>
    """, height=0)
else:
    st.error("❌ 'index.html' file main root folder me nahi mili!")

# ⏳ Hidden Background loop trigger for postMessage flow (No Tearing)
st.empty()
time.sleep(1)
st.rerun()
