import sys
import os
import time
import json
import sqlite3
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')
DB_PATH = os.path.join(BASE_DIR, "market_ticks.db")

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ==============================================================================
# 🗄️ 1. LOCAL DATA CORE: DATABASE ENGINE SETUP
# ==============================================================================
def init_market_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            asset TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            PRIMARY KEY (asset, timestamp)
        )
    """)
    conn.commit()
    conn.close()

init_market_db()

# ==============================================================================
# 🔌 2. SDK BROKER PIPELINE CONNECTIONS
# ==============================================================================
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

# Realistic pricing configurations
base_val = 24350.0 if target_index == "NIFTY" else 79650.0

# ==============================================================================
# 🧠 3. DATABASE INJECTOR & STREAM BUFFER LAYER
# ==============================================================================
# A. Fetch Fresh Real Data from Broker SDK and Commit to SQLite
if market_engine:
    try:
        symbol_name = "Nifty 50" if target_index == "NIFTY" else "SENSEX"
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        
        # 1. Historical fetch to build strong database foundation
        hist_response = market_engine.historical_data({
            "exchange": exch_name, "type": "INDEX", "values": [symbol_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "5m", "intraDay": True, "realTime": False
        })
        
        if hist_response and hasattr(hist_response, 'candles') and hist_response.candles:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for candle in hist_response.candles:
                raw_ts = getattr(candle, 'timestamp', '')
                if raw_ts:
                    unix_ts = int(pd.to_datetime(raw_ts).timestamp())
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (target_index, unix_ts, float(getattr(candle, 'open', 0)) / 100, 
                          float(getattr(candle, 'high', 0)) / 100, float(getattr(candle, 'low', 0)) / 100, 
                          float(getattr(candle, 'close', 0)) / 100))
            conn.commit()
            conn.close()

        # 2. Live Spot updates processing directly inside SQLite matrix
        snap = market_engine.current_price(target_index, exchange=exch_name)
        if snap and getattr(snap, 'price', None):
            base_val = float(snap.price) / 100
            current_rounded_unix = (int(time.time()) // 300) * 300  # Sync with 5m candle window block
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Check if active bar node already exists in file storage
            cursor.execute("SELECT open, high, low FROM market_history WHERE asset=? AND timestamp=?", (target_index, current_rounded_unix))
            existing_node = cursor.fetchone()
            
            if existing_node:
                new_high = max(existing_node[1], base_val)
                new_low = min(existing_node[2], base_val)
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timestamp=?
                """, (new_high, new_low, base_val, target_index, current_rounded_unix))
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO market_history (asset, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (target_index, current_rounded_unix, base_val, base_val, base_val, base_val))
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 📊 4. HARD DRIVE RECOVERY ENGINE (Ensures Chart Renders from Local Storage)
# ==============================================================================
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? ORDER BY timestamp ASC LIMIT 300
    """, (target_index,))
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        master_history_array.append({
            "time": int(row[0]), "open": row[1], "high": row[2], "low": row[3], "close": row[4]
        })
except Exception:
    pass

# Strong hardcoded generator backup pattern if DB engine is entirely empty
if not master_history_array:
    current_unix_anchor = (int(time.time()) // 300) * 300
    for step in range(120):
        computed_time = current_unix_anchor - ((120 - step) * 300)
        master_history_array.append({
            "time": int(computed_time),
            "open": base_val + (step * 0.1), "high": base_val + (step * 0.1) + 6,
            "low": base_val + (step * 0.1) - 4, "close": base_val + (step * 0.1) + 2
        })

if master_history_array:
    base_val = master_history_array[-1]["close"]

runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.caption("💾 Backend Storage Engine: ACTIVE")

# ==============================================================================
# 🌐 5. HTML TRANSMISSION INTERFACE
# ==============================================================================
if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(runtime_payload)
    
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
        
        setTimeout(function() {{
            const iframeWin = document.getElementsByTagName('iframe')[0]?.contentWindow || window;
            iframeWin.postMessage({{ 
                type: "LIVE_TICK_UPDATE", 
                payload: {json_data}, 
                asset: "{target_index}" 
            }}, "*");
        }}, 250);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=760, scrolling=False)
    
    time.sleep(1.5)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
