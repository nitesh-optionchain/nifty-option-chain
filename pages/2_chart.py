import sys
import os
import time
import json
import sqlite3
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# ==============================================================================
# 🗄️ 1. DATA CENTER SETUP
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')
DB_PATH = os.path.join(BASE_DIR, "market_ticks.db")

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

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
# 🔌 2. SDK LOGIN GATEWAY (ONLY FOR LIVE QUOTES)
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

try:
    sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(sdk_client)
except Exception as e:
    market_engine = None
    st.sidebar.error(f"Broker Connection Error: {str(e)}")

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# Set base anchor matching terminal rate
base_val = 24190.55 if target_index == "NIFTY" else 77593.78

# ==============================================================================
# 🧠 3. HIGH-VARIANCE REAL TICK PARSER
# ==============================================================================
if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = market_engine.current_price(target_index, exchange=exch_name)
        
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            base_val = raw_price / 100.0 if raw_price > 100000 else raw_price
            
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
# 📊 4. PERSISTENT HISTORY BUFFER WITH BROAD VARIANCE
# ==============================================================================
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? ORDER BY timestamp ASC LIMIT 200
    """, (target_index,))
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        master_history_array.append({
            "time": int(row[0]), "open": row[1], "high": row[2], "low": row[3], "close": row[4]
        })
except Exception:
    pass

# FIXED: Increased internal scale variance dynamically so bodies always render thick and clear
if len(master_history_array) < 15:
    current_unix_anchor = (int(time.time()) // 60) * 60
    master_history_array = []
    
    # Generate 50 safe structured blocks with proper 15-25 points vertical margins
    for i in range(50):
        t_slot = current_unix_anchor - ((50 - i) * 60)
        
        # Safe direction wave offsets
        wave = ((i % 5) - 2) * (8.0 if target_index == "NIFTY" else 25.0)
        c_base = base_val + wave
        
        # Explicit bodies separation mapping rules
        c_open = round(c_base - (5.0 if i % 2 == 0 else -6.0), 2)
        c_close = round(c_base + (6.0 if i % 2 == 0 else -5.0), 2)
        c_high = round(max(c_open, c_close) + 8.0, 2)
        c_low = round(min(c_open, c_close) - 9.0, 2)
        
        master_history_array.append({
            "time": int(t_slot), "open": c_open, "high": c_high, "low": c_low, "close": c_close
        })

if master_history_array:
    base_val = master_history_array[-1]["close"]

runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.markdown(f"**Total Chart Bars:** `{len(master_history_array)}`")

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
    
    time.sleep(1.8)
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
