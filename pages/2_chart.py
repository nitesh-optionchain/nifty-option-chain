import sys
from types import ModuleType
import os
import time
import json
import sqlite3
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

# 📊 Wide mode configuration
st.set_page_config(layout="wide")

# 🚀 Anti-Crash Pandas Bypass Engine
if 'pandas' not in sys.modules:
    fake_pandas = ModuleType('pandas')
    fake_pandas.DataFrame = lambda *args, **kwargs: None
    sys.modules['pandas'] = fake_pandas

# 📂 Paths Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')
DB_PATH = os.path.join(BASE_DIR, "user_management.db")

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ==============================================================================
# 🗄️ 1. SECURE SQLITE USER DATABASE INITIALIZATION
# ==============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, created_at) VALUES ('admin', 'Admin Chief', ?)", (str(datetime.now()),))
    conn.commit()
    conn.close()

init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ==============================================================================
# 🔒 SECURITY GATEWAY INTERFACE (ADMIN CHIEF LAYER)
# ==============================================================================
if not st.session_state.authenticated:
    st.subheader("🔒 Terminal Access Controller")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("🔐 Access Required: Enterprise dashboard layout locked behind SQLite security enforcer.")
        login_id = st.text_input("User ID Key", type="password", placeholder="Enter your access credentials...")
        
        if st.button("Verify Authentication", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (login_id,))
            user_row = cursor.fetchone()
            conn.close()
            
            if user_row:
                st.session_state.authenticated = True
                st.session_state.current_user = user_row[0]
                st.success(f"🔓 Access Granted. Welcome {user_row[0]}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid User Access Key Pattern. Connection refused.")
    st.stop()

# ==============================================================================
# 📊 MAIN SECURE DASHBOARD (AUTHENTICATED MODE)
# ==============================================================================
# Header UI with Active Logout Control
h_left, h_right = st.columns([6, 2])
with h_left:
    st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
with h_right:
    st.write(f"👤 **User:** {st.session_state.current_user}")
    if st.button("🔒 Secure Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

st.markdown("---")

# 🔌 BROKER INTERFACES CONNECTIONS
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
    st.sidebar.error(f"SDK Engine Error: {str(e)}")

if "master_storage" not in st.session_state:
    st.session_state.master_storage = {
        "NIFTY": {"price": 0, "status": "LIVE", "master_history": []},
        "SENSEX": {"price": 0, "status": "LIVE", "master_history": []}
    }

if not market_engine:
    st.error("🔒 Auth Fail: Broker connection structure ready nahi ho paya. Please verify your system tokens.")
    st.stop()

# 🌐 HTML JavaScript Frame Injector WITH DYNAMIC LIVE DATA PUSHER LOOP
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Dynamic ticks fetch from market engine
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
        st.sidebar.warning(f"Tick collect alert: {data_err}")

    # JSON dynamic generation
    json_data = json.dumps(st.session_state.master_storage)

    # 🎯 POSTMESSAGE CONTROLLER BRIDGE
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
    
    # Render component canvas frame
    components.html(html_content, height=850, scrolling=True)
    
    # ⏳ Background dynamic synchronizer loop
    time.sleep(1)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
