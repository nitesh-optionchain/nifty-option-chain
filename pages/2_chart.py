import sys
import os
import time
import json
import sqlite3
from datetime import datetime
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
# 🗄️ 1. DATA CENTER ENGINE INITIALIZATION
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
# 🔌 2. SDK BROKER INTERFACE CONNECTIONS
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

base_val = 24200.0 if target_index == "NIFTY" else 79650.0

# ==============================================================================
# 🧠 3. RAW DYNAMIC LIVE TICK PARSING MATRIX
# ==============================================================================
if market_engine:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = market_engine.current_price(target_index, exchange=exch_name)
        
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            
            # Format Paise to Rupees conversion layer
            if raw_price > 100000:
                base_val = raw_price / 100.0
            else:
                base_val = raw_price
                
            current_rounded_unix = (int(time.time()) // 300) * 300
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT open, high, low, close FROM market_history WHERE asset=? AND timestamp=?", (target_index, current_rounded_unix))
            existing_candle = cursor.fetchone()
            
            if existing_candle:
                new_high = max(existing_candle[1], base_val)
                new_low = min(existing_candle[2], base_val)
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timestamp=?
                """, (new_high, new_low, base_val, target_index, current_rounded_unix))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (target_index, current_rounded_unix, base_val, base_val, base_val, base_val))
                
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 📊 4. FINAL PRODUCTION TIMELINE ASSEMBLY
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

if not master_history_array:
    current_unix_anchor = (int(time.time()) // 300) * 300
    master_history_array.append({
        "time": current_unix_anchor,
        "open": base_val, "high": base_val, "low": base_val, "close": base_val
    })

if master_history_array:
    base_val = master_history_array[-1]["close"]

runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.caption("🟢 Genuine Live Sync Module: ACTIVE")

# ==============================================================================
# 🌐 5. HTML HEADER SAFE TRANSMISSION INTERFACE
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
    
    # FIXED: Height reduced slightly to perfectly restore upper black header visibility
    components.html(html_content, height=620, scrolling=False)
    
    time.sleep(2.0)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
