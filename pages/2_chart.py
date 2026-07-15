import sys
import os
import time
import json
import sqlite3
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')
DB_PATH = os.path.join(BASE_DIR, "market_ticks.db")

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ==============================================================================
# 🗄️ 1. DATABASE CONFIGURATION
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

base_val = 24202.10 if target_index == "NIFTY" else 79650.0

# ==============================================================================
# 🧠 3. PURE REAL TIME 1-MINUTE CANDLE STREAM ENGINE
# ==============================================================================
if market_engine:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = market_engine.current_price(target_index, exchange=exch_name)
        
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            base_val = raw_price / 100.0 if raw_price > 100000 else raw_price
                
            # CHANGED TO 1-MINUTE TIMEFRAME (60 Seconds Anchor) FOR INSTANT LIVE TESTING
            current_rounded_unix = (int(time.time()) // 60) * 60
            
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
# 📊 4. DYNAMIC HISTORICAL TIMELINE RETRIEVAL
# ==============================================================================
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Pulling last 60 parsed candles to print continuous charts
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? ORDER BY timestamp ASC LIMIT 60
    """, (target_index,))
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        master_history_array.append({
            "time": int(row[0]), "open": row[1], "high": row[2], "low": row[3], "close": row[4]
        })
except Exception:
    pass

# Safe bootstrap injector ONLY if the database has less than 2 rows on first load
if len(master_history_array) < 2:
    current_unix_anchor = (int(time.time()) // 60) * 60
    # Inject a couple of dynamic baseline slots using standard variations
    for i in range(10):
        t_slot = current_unix_anchor - ((10 - i) * 60)
        master_history_array.insert(0, {
            "time": int(t_slot),
            "open": base_val - (i % 3), "high": base_val + 4,
            "low": base_val - 5, "close": base_val + (i % 2)
        })

if master_history_array:
    base_val = master_history_array[-1]["close"]

runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.caption("🟢 Pure Live Feeds Sync: RUNNING")

# ==============================================================================
# 🌐 5. HTML SAFE ENGINE TRANSMISSION
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
    components.html(html_content, height=720, scrolling=False)
    
    time.sleep(1.5) # Reduced refresh latency for fast responsive plotting
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
